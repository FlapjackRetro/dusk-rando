using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Net.Security;
using System.Net.Sockets;
using System.Reflection;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Converters;
using Archipelago.MultiClient.Net.Helpers;
using Newtonsoft.Json;

namespace DuskRando
{
    /// <summary>
    /// Issue #24: the server warns "your client does not support compressed websocket connections".
    ///
    /// Archipelago asks clients to support per-message compression (permessage-deflate, RFC 7692; see
    /// "Websocket connections should support per-message compression" in docs/network protocol.md).
    /// Archipelago.MultiClient.Net only turns it on in its .NET 6 build (ClientWebSocket.DangerousDeflateOptions);
    /// DUSK's Mono runtime gets the .NET Framework build, whose ClientWebSocket can't negotiate extensions.
    ///
    /// So the mod brings its own small RFC 6455 client and plugs it into MultiClient.Net through its public
    /// IArchipelagoSocketHelper interface. It offers
    /// <c>permessage-deflate; client_no_context_takeover; server_no_context_takeover</c>:
    /// - the server compresses everything it sends (room info, data package, items...), which is where nearly
    ///   all the traffic is; each message is inflated on its own because of server_no_context_takeover;
    /// - our own messages are small and go out uncompressed, which RFC 7692 allows (RSV1 clear).
    /// Checked against Archipelago's MultiServer (websockets 13): the extension is accepted, every server
    /// message arrives compressed, and the warning is no longer sent.
    /// </summary>
    public sealed class CompressedSocketHelper : IArchipelagoSocketHelper
    {
        static readonly ArchipelagoPacketConverter Converter = new ArchipelagoPacketConverter();

        public event ArchipelagoSocketHelperDelagates.PacketReceivedHandler PacketReceived;
        public event ArchipelagoSocketHelperDelagates.PacketsSentHandler PacketsSent;
        public event ArchipelagoSocketHelperDelagates.ErrorReceivedHandler ErrorReceived;
        public event ArchipelagoSocketHelperDelagates.SocketClosedHandler SocketClosed;
        public event ArchipelagoSocketHelperDelagates.SocketOpenedHandler SocketOpened;

        public Uri Uri { get; }
        public bool Connected => ws != null && ws.IsOpen;
        public bool Compressed => ws != null && ws.Deflate;

        WebSocketConnection ws;
        int closedRaised;

        public CompressedSocketHelper(Uri uri) { Uri = uri; }

        public Task ConnectAsync() => Task.Run(() =>
        {
            // Same rule as MultiClient.Net: no scheme given -> try wss first, then ws.
            if (Uri.Scheme == "unspecified")
            {
                try { ws = WebSocketConnection.Open(WithScheme(Uri, "wss")); }
                catch (Exception first)
                {
                    try { ws = WebSocketConnection.Open(WithScheme(Uri, "ws")); }
                    catch (Exception second) { Error(new AggregateException(first, second)); throw; }
                }
            }
            else
            {
                try { ws = WebSocketConnection.Open(Uri); }
                catch (Exception e) { Error(e); throw; }
            }
            Plugin.Log.LogInfo($"Connected to {ws.Uri} ({(ws.Deflate ? "compressed" : "uncompressed")})");
            SocketOpened?.Invoke();
            var reader = new Thread(ReadLoop) { IsBackground = true, Name = "DuskRando AP socket" };
            reader.Start();
        });

        static Uri WithScheme(Uri uri, string scheme) =>
            new UriBuilder(uri) { Scheme = scheme, Port = uri.Port }.Uri;

        void ReadLoop()
        {
            try
            {
                while (ws.IsOpen)
                {
                    var message = ws.ReadMessage();
                    if (message == null) break; // closed
                    List<ArchipelagoPacketBase> packets;
                    try { packets = JsonConvert.DeserializeObject<List<ArchipelagoPacketBase>>(message, Converter); }
                    catch (Exception e) { Error(e); continue; }
                    if (packets == null) continue;
                    foreach (var p in packets)
                    {
                        try { PacketReceived?.Invoke(p); }
                        catch (Exception e) { Error(e); }
                    }
                }
            }
            catch (Exception e)
            {
                if (ws.IsOpen) Error(e);
            }
            finally
            {
                ws.Abort();
                RaiseClosed("connection closed");
            }
        }

        void RaiseClosed(string reason)
        {
            if (Interlocked.Exchange(ref closedRaised, 1) == 0) SocketClosed?.Invoke(reason);
        }

        void Error(Exception e)
        {
            try { ErrorReceived?.Invoke(e, e.Message); } catch { /* ignored */ }
        }

        public Task DisconnectAsync() => Task.Run(() =>
        {
            ws?.Close();
            RaiseClosed("Closure requested by client");
        });

        public void SendPacket(ArchipelagoPacketBase packet) => SendMultiplePackets(new[] { packet });
        public void SendMultiplePackets(List<ArchipelagoPacketBase> packets) => SendMultiplePackets(packets.ToArray());
        public void SendMultiplePackets(params ArchipelagoPacketBase[] packets) => Send(packets);

        public Task SendPacketAsync(ArchipelagoPacketBase packet) => SendMultiplePacketsAsync(new[] { packet });
        public Task SendMultiplePacketsAsync(List<ArchipelagoPacketBase> packets) => SendMultiplePacketsAsync(packets.ToArray());
        public Task SendMultiplePacketsAsync(params ArchipelagoPacketBase[] packets) => Task.Run(() => Send(packets));

        void Send(ArchipelagoPacketBase[] packets)
        {
            if (!Connected) throw new Archipelago.MultiClient.Net.Exceptions.ArchipelagoSocketClosedException();
            ws.SendText(JsonConvert.SerializeObject(packets));
            try { PacketsSent?.Invoke(packets); } catch (Exception e) { Error(e); }
        }
    }

    /// <summary>A minimal RFC 6455 client: handshake, masked text frames out, inflating reads in.</summary>
    sealed class WebSocketConnection
    {
        const string Guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
        const string Offer = "permessage-deflate; client_no_context_takeover; server_no_context_takeover";
        const int ConnectTimeoutMs = 10000;
        static readonly byte[] DeflateTail = { 0x00, 0x00, 0xFF, 0xFF };

        public Uri Uri { get; private set; }
        public bool Deflate { get; private set; }
        public bool IsOpen => open && tcp != null && tcp.Connected;

        TcpClient tcp;
        Stream stream;
        volatile bool open;
        bool closeSent;
        readonly object sendLock = new object();
        readonly RandomNumberGenerator rng = RandomNumberGenerator.Create();

        public static WebSocketConnection Open(Uri uri)
        {
            var c = new WebSocketConnection { Uri = uri };
            try { c.Handshake(); }
            catch { c.Abort(); throw; }
            return c;
        }

        void Handshake()
        {
            bool secure = Uri.Scheme == "wss";
            int port = Uri.Port > 0 ? Uri.Port : (secure ? 443 : 80);
            tcp = new TcpClient { NoDelay = true };
            var pending = tcp.BeginConnect(Uri.Host, port, null, null);
            if (!pending.AsyncWaitHandle.WaitOne(ConnectTimeoutMs)) throw new TimeoutException($"Timed out connecting to {Uri.Host}:{port}");
            tcp.EndConnect(pending);
            // Don't let a silent server (e.g. TLS offered to a plain ws server) hang the handshake.
            tcp.ReceiveTimeout = tcp.SendTimeout = ConnectTimeoutMs;
            stream = tcp.GetStream();
            if (secure)
            {
                var ssl = new SslStream(stream, false);
                ssl.AuthenticateAsClient(Uri.Host, null, SslProtocols.Tls12, false);
                stream = ssl;
            }

            var keyBytes = new byte[16];
            rng.GetBytes(keyBytes);
            var key = Convert.ToBase64String(keyBytes);
            bool offerDeflate = InflateWorks();
            var path = string.IsNullOrEmpty(Uri.PathAndQuery) ? "/" : Uri.PathAndQuery;
            var request = new StringBuilder()
                .Append("GET ").Append(path).Append(" HTTP/1.1\r\n")
                .Append("Host: ").Append(Uri.Host).Append(':').Append(port).Append("\r\n")
                .Append("Upgrade: websocket\r\nConnection: Upgrade\r\n")
                .Append("Sec-WebSocket-Key: ").Append(key).Append("\r\n")
                .Append("Sec-WebSocket-Version: 13\r\n");
            if (offerDeflate) request.Append("Sec-WebSocket-Extensions: ").Append(Offer).Append("\r\n");
            request.Append("User-Agent: DuskRando\r\n\r\n");
            var bytes = Encoding.ASCII.GetBytes(request.ToString());
            stream.Write(bytes, 0, bytes.Length);
            stream.Flush();

            var headers = ReadHttpHeaders(out var statusLine);
            if (!statusLine.Contains(" 101")) throw new IOException("WebSocket handshake refused: " + statusLine);
            string expected;
            using (var sha = SHA1.Create())
                expected = Convert.ToBase64String(sha.ComputeHash(Encoding.ASCII.GetBytes(key + Guid)));
            if (!headers.TryGetValue("sec-websocket-accept", out var accept) || accept != expected)
                throw new IOException("WebSocket handshake: bad Sec-WebSocket-Accept");
            Deflate = offerDeflate && headers.TryGetValue("sec-websocket-extensions", out var ext) &&
                      ext.TrimStart().StartsWith("permessage-deflate", StringComparison.OrdinalIgnoreCase);
            tcp.ReceiveTimeout = tcp.SendTimeout = 0; // the server can be quiet for a long time once connected
            open = true;
        }

        Dictionary<string, string> ReadHttpHeaders(out string statusLine)
        {
            var sb = new StringBuilder();
            while (!sb.ToString().EndsWith("\r\n\r\n"))
            {
                int b = stream.ReadByte();
                if (b < 0) throw new IOException("Connection closed during WebSocket handshake");
                sb.Append((char)b);
                if (sb.Length > 16384) throw new IOException("WebSocket handshake response too long");
            }
            var lines = sb.ToString().Split(new[] { "\r\n" }, StringSplitOptions.RemoveEmptyEntries);
            statusLine = lines.Length > 0 ? lines[0] : "";
            var headers = new Dictionary<string, string>();
            for (int i = 1; i < lines.Length; i++)
            {
                int colon = lines[i].IndexOf(':');
                if (colon > 0) headers[lines[i].Substring(0, colon).Trim().ToLowerInvariant()] = lines[i].Substring(colon + 1).Trim();
            }
            return headers;
        }

        /// <summary>Read one whole message. Null when the server closes the connection.</summary>
        public string ReadMessage()
        {
            var data = new MemoryStream();
            bool started = false, compressed = false;
            while (true)
            {
                int b0 = ReadByteOrThrow(), b1 = ReadByteOrThrow();
                bool fin = (b0 & 0x80) != 0, rsv1 = (b0 & 0x40) != 0;
                int opcode = b0 & 0x0F;
                long length = b1 & 0x7F;
                if (length == 126) length = (ReadByteOrThrow() << 8) | ReadByteOrThrow();
                else if (length == 127)
                {
                    length = 0;
                    for (int i = 0; i < 8; i++) length = (length << 8) | (uint)ReadByteOrThrow();
                }
                byte[] mask = (b1 & 0x80) != 0 ? ReadExactly(4) : null;
                var payload = ReadExactly(checked((int)length));
                if (mask != null) for (int i = 0; i < payload.Length; i++) payload[i] ^= mask[i % 4];

                switch (opcode)
                {
                    case 0x9: SendFrame(0xA, payload); continue;        // ping -> pong
                    case 0xA: continue;                                 // pong
                    case 0x8:                                           // close: echo it and stop
                        try { SendFrame(0x8, payload.Length >= 2 ? new[] { payload[0], payload[1] } : new byte[0]); }
                        catch { /* already gone */ }
                        open = false;
                        return null;
                    case 0x1:
                    case 0x2:
                        started = true;
                        compressed = rsv1;
                        data.SetLength(0);
                        data.Write(payload, 0, payload.Length);
                        break;
                    case 0x0:
                        data.Write(payload, 0, payload.Length);
                        break;
                }
                if (!fin || !started) continue;
                var body = data.ToArray();
                if (compressed) body = Inflate(body);
                return Encoding.UTF8.GetString(body);
            }
        }

        /// <summary>RFC 7692: append 00 00 FF FF to the message and inflate it as raw DEFLATE.</summary>
        static byte[] Inflate(byte[] data)
        {
            var input = new MemoryStream(data.Length + 4);
            input.Write(data, 0, data.Length);
            input.Write(DeflateTail, 0, DeflateTail.Length);
            input.Position = 0;
            var output = new MemoryStream(data.Length * 4);
            using (var inflater = new DeflateStream(input, CompressionMode.Decompress))
            {
                var buffer = new byte[16384];
                int n;
                while ((n = inflater.Read(buffer, 0, buffer.Length)) > 0) output.Write(buffer, 0, n);
            }
            return output.ToArray();
        }

        /// <summary>
        /// Only offer compression if this runtime can inflate a real permessage-deflate payload (Mono's
        /// DeflateStream relies on MonoPosixHelper, which DUSK ships; this guards against it being missing).
        /// The sample is [{"cmd":"Bounced"}] compressed by zlib with a sync flush and the 00 00 FF FF removed.
        /// </summary>
        static bool InflateWorks()
        {
            try
            {
                var sample = new byte[] { 0x8A, 0xAE, 0x56, 0x4A, 0xCE, 0x4D, 0x51, 0xB2, 0x52, 0x72, 0xCA, 0x2F, 0xCD,
                                          0x4B, 0x4E, 0x4D, 0x51, 0xAA, 0x8D, 0x05, 0x00 };
                return Encoding.UTF8.GetString(Inflate(sample)) == "[{\"cmd\":\"Bounced\"}]";
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("Websocket compression unavailable: " + e.Message);
                return false;
            }
        }

        public void SendText(string text) => SendFrame(0x1, Encoding.UTF8.GetBytes(text));

        void SendFrame(int opcode, byte[] payload)
        {
            lock (sendLock)
            {
                if (closeSent) return;
                var header = new MemoryStream(14);
                header.WriteByte((byte)(0x80 | opcode)); // FIN, no RSV bits: sent uncompressed
                if (payload.Length < 126) header.WriteByte((byte)(0x80 | payload.Length));
                else if (payload.Length <= ushort.MaxValue)
                {
                    header.WriteByte(0x80 | 126);
                    header.WriteByte((byte)(payload.Length >> 8));
                    header.WriteByte((byte)payload.Length);
                }
                else
                {
                    header.WriteByte(0x80 | 127);
                    for (int i = 7; i >= 0; i--) header.WriteByte((byte)((long)payload.Length >> (8 * i)));
                }
                var mask = new byte[4];
                rng.GetBytes(mask);
                header.Write(mask, 0, 4);
                var masked = new byte[payload.Length];
                for (int i = 0; i < payload.Length; i++) masked[i] = (byte)(payload[i] ^ mask[i % 4]);
                var h = header.ToArray();
                stream.Write(h, 0, h.Length);
                stream.Write(masked, 0, masked.Length);
                stream.Flush();
                if (opcode == 0x8) closeSent = true;
            }
        }

        public void Close()
        {
            try { if (IsOpen) SendFrame(0x8, new byte[] { 0x03, 0xE8 }); } // 1000 normal closure
            catch { /* ignored */ }
            Abort();
        }

        public void Abort()
        {
            open = false;
            try { stream?.Dispose(); } catch { /* ignored */ }
            try { tcp?.Close(); } catch { /* ignored */ }
        }

        int ReadByteOrThrow()
        {
            int b = stream.ReadByte();
            if (b < 0) throw new IOException("connection closed");
            return b;
        }

        byte[] ReadExactly(int count)
        {
            var buffer = new byte[count];
            int read = 0;
            while (read < count)
            {
                int n = stream.Read(buffer, read, count - read);
                if (n <= 0) throw new IOException("connection closed");
                read += n;
            }
            return buffer;
        }
    }

    /// <summary>
    /// Builds an ArchipelagoSession around our own socket. This mirrors ArchipelagoSessionFactory.CreateSession
    /// in Archipelago.MultiClient.Net 6.7.1 (the version the csproj pins); the helpers' constructors are internal,
    /// so they're called by reflection. If anything doesn't match, Create throws and the caller falls back to the
    /// library's own (uncompressed) factory.
    /// </summary>
    static class CompressedSession
    {
        public static ArchipelagoSession Create(string host, out CompressedSocketHelper socket)
        {
            socket = new CompressedSocketHelper(ParseUri(host, 38281));
            var asm = typeof(ArchipelagoSession).Assembly;
            object New(string type, params object[] args) =>
                Activator.CreateInstance(asm.GetType(type, true),
                    BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic, null, args, null);

            const string H = "Archipelago.MultiClient.Net.Helpers.", D = "Archipelago.MultiClient.Net.DataPackage.";
            var cache = New(D + "DataPackageCache", socket);
            var connection = New(H + "ConnectionInfoHelper", socket);
            var players = New(H + "PlayerHelper", socket, connection);
            var resolver = New(D + "ItemInfoResolver", cache, connection);
            var locations = New(H + "LocationCheckHelper", socket, resolver, connection, players);
            var items = New(H + "ReceivedItemsHelper", socket, locations, resolver, connection, players);
            var room = New(H + "RoomStateHelper", socket, locations);
            var storage = New(H + "DataStorageHelper", socket, connection);
            var log = New(H + "MessageLogHelper", socket, resolver, players, connection);
            var hints = New(H + "HintsHelper", socket, players, locations, room, storage);
            return (ArchipelagoSession)New("Archipelago.MultiClient.Net.ArchipelagoSession",
                socket, items, locations, players, room, connection, storage, log, hints);
        }

        /// <summary>Same parsing as ArchipelagoSessionFactory.ParseUri.</summary>
        static Uri ParseUri(string hostname, int port)
        {
            var uri = hostname.Trim();
            if (!uri.StartsWith("ws://") && !uri.StartsWith("wss://")) uri = "unspecified://" + uri;
            if (!uri.Substring(uri.IndexOf("://", StringComparison.Ordinal) + 3).Contains(":")) uri += ":" + port;
            if (uri.EndsWith(":")) uri += port;
            return new Uri(uri);
        }
    }
}
