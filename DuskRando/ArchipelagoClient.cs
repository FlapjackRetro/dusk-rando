using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.BounceFeatures.DeathLink;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Models;
using Archipelago.MultiClient.Net.Packets;
using Newtonsoft.Json.Linq;

namespace DuskRando
{
    /// <summary>One received item. (No ValueTuple: it isn't guaranteed in DUSK's Mono runtime.)</summary>
    public struct Received
    {
        public readonly int Index;
        public readonly string Name, Sender;
        public Received(int index, string name, string sender) { Index = index; Name = name; Sender = sender; }
    }

    public class ScoutEntry
    {
        public string ItemName;   // e.g. "Progressive Shotgun"
        public bool ForDusk;      // a DUSK item for this player, so it can wear its DUSK model
        public ItemFlags Flags;
        public string Display;    // text shown when it's picked up
    }

    /// <summary>Owns the Archipelago session. Network callbacks only enqueue; the game thread drains in Update.</summary>
    public class ArchipelagoClient
    {
        public const string Game = "DUSK";

        public ArchipelagoSession Session { get; private set; }
        public bool Connected => Session != null && Session.Socket.Connected;
        public string Status = "Not connected";

        /// <summary>Seed + slot, safe for file names. Kept while the connection drops; cleared on Disconnect.</summary>
        public string SeedKey { get; private set; }

        static string SafeFileName(string s)
        {
            var bad = System.IO.Path.GetInvalidFileNameChars();
            var chars = s.ToCharArray();
            for (int i = 0; i < chars.Length; i++)
                if (Array.IndexOf(bad, chars[i]) >= 0 || chars[i] == '?' || chars[i] == ' ') chars[i] = '_';
            return new string(chars);
        }

        public HashSet<string> Levels = new HashSet<string>();
        public HashSet<string> Categories = new HashSet<string>();
        public string Goal = "bosses";
        DeathLinkService deathLink;

        readonly object queueLock = new object();
        readonly Queue<Received> incoming = new Queue<Received>();
        readonly Queue<string> pendingDeaths = new Queue<string>();

        /// <summary>Every item received so far, by item name, for state-like items (access, keys, weapons).</summary>
        public readonly Dictionary<string, int> ReceivedCounts = new Dictionary<string, int>();
        /// <summary>What sits at each of our locations (filled asynchronously after connecting).</summary>
        public readonly Dictionary<long, ScoutEntry> Scouted = new Dictionary<long, ScoutEntry>();
        /// <summary>Set by the network thread when scouting finished; the game thread clears it after use.</summary>
        public volatile bool ScoutsArrived;
        int processedIndex = -1;
        int receivedCounter;
        int highestSeen = -1;
        string saveKey;

        public void Connect(string host, string slot, string password)
        {
            Disconnect();
            try
            {
                Session = ArchipelagoSessionFactory.CreateSession(host);
                lock (Scouted) Scouted.Clear();
                ScoutsArrived = false;
                ReceivedCounts.Clear();
                lock (queueLock) { incoming.Clear(); receivedCounter = 0; }
                deferred.Clear();
                highestSeen = -1;
                // Attach before logging in so the initial ReceivedItems packet goes through the handler.
                Session.Items.ItemReceived += OnItemReceived;
                var result = Session.TryConnectAndLogin(Game, slot, ItemsHandlingFlags.AllItems,
                    new Version(0, 6, 0), tags: new string[0], password: string.IsNullOrEmpty(password) ? null : password,
                    requestSlotData: true);
                if (!(result is LoginSuccessful ok))
                {
                    var f = (LoginFailure)result;
                    Status = "Failed: " + string.Join(", ", f.Errors);
                    Session = null;
                    return;
                }
                ReadSlotData(ok.SlotData);
                saveKey = $"{Session.RoomState.Seed}_{slot}";
                SeedKey = SafeFileName(saveKey);
                try { System.IO.Directory.CreateDirectory(Patches.SeedStats.Directory); }
                catch (Exception e) { Plugin.Log.LogWarning("Could not create seed stats folder: " + e.Message); }
                processedIndex = LoadProcessedIndex();
                if (ok.SlotData.TryGetValue("death_link", out var dl) && Convert.ToBoolean(dl))
                {
                    deathLink = Session.CreateDeathLinkService();
                    deathLink.OnDeathLinkReceived += d => { lock (queueLock) pendingDeaths.Enqueue(d.Source); };
                    deathLink.EnableDeathLink();
                }
                activeLocations = new HashSet<long>(Session.Locations.AllLocations);
                lock (checkedLocations)
                {
                    checkedLocations.Clear();
                    checkedLocations.UnionWith(Session.Locations.AllLocationsChecked);
                }
                Session.Locations.CheckedLocationsUpdated += ids => { lock (checkedLocations) checkedLocations.UnionWith(ids); };
                Scout();
                Status = $"Connected as {slot}";
                Plugin.Log.LogInfo(Status);
            }
            catch (Exception e)
            {
                Status = "Error: " + e.Message;
                Plugin.Log.LogError(e);
                Session = null;
            }
        }

        public void Disconnect()
        {
            if (Session != null)
            {
                try { Session.Socket.DisconnectAsync(); } catch { /* ignored */ }
            }
            Session = null;
            deathLink = null;
            SeedKey = null;
            Status = "Not connected";
        }

        void ReadSlotData(Dictionary<string, object> data)
        {
            Levels = new HashSet<string>(((JArray)data["levels"]).Select(t => (string)t));
            Categories = new HashSet<string>(((JArray)data["categories"]).Select(t => (string)t));
            Goal = Convert.ToString(data["goal"]);
        }

        void OnItemReceived(Archipelago.MultiClient.Net.Helpers.ReceivedItemsHelper helper)
        {
            lock (queueLock)
            {
                // helper.Index is the total received count, so number the items ourselves. With
                // ItemsHandlingFlags.AllItems the server replays the full list from 0 on every connect.
                while (helper.Any())
                {
                    var item = helper.DequeueItem();
                    incoming.Enqueue(new Received(receivedCounter++, item.ItemName, item.Player.Name));
                }
            }
        }

        void Scout()
        {
            var ids = Session.Locations.AllLocations.ToArray();
            int mySlot = Session.ConnectionInfo.Slot;
            Session.Locations.ScoutLocationsAsync(HintCreationPolicy.None, ids).ContinueWith(t =>
            {
                if (t.IsFaulted) { Plugin.Log.LogWarning("Scouting failed: " + t.Exception?.GetBaseException().Message); return; }
                lock (Scouted)
                    foreach (var kv in t.Result)
                    {
                        var info = kv.Value;
                        bool mine = info.Player.Slot == mySlot;
                        Scouted[kv.Key] = new ScoutEntry
                        {
                            ItemName = info.ItemDisplayName,
                            ForDusk = mine && info.ItemGame == Game,
                            Flags = info.Flags,
                            // Name the other world's player and game, so e.g. DOOM's "Tower of Babel (E2M8)"
                            // isn't mistaken for DUSK's E2M8 (issue #19).
                            Display = mine ? info.ItemDisplayName
                                           : $"{info.ItemDisplayName} for {info.Player.Name} ({info.ItemGame})",
                        };
                    }
                ScoutsArrived = true;
            });
        }

        public ScoutEntry GetScout(long id)
        {
            lock (Scouted) return Scouted.TryGetValue(id, out var s) ? s : null;
        }

        // New items whose effect needs the player in a level (ammo, health, powerups, weapons while in menus).
        readonly List<Received> deferred = new List<Received>();

        /// <summary>Called every frame from the game thread.</summary>
        public void Pump(Action<string, string, bool> applyItem, Action<string> onDeath)
        {
            bool changed = false;
            while (true)
            {
                Received next;
                lock (queueLock)
                {
                    if (incoming.Count == 0) break;
                    next = incoming.Dequeue();
                }
                ReceivedCounts.TryGetValue(next.Name, out var c);
                ReceivedCounts[next.Name] = c + 1;
                bool isNew = next.Index > processedIndex;
                if (isNew && !ItemGiver.CanApplyNow(next.Name)) deferred.Add(next);
                else applyItem(next.Name, next.Sender, isNew);
                if (isNew) changed = true;
                highestSeen = Math.Max(highestSeen, next.Index);
            }
            if (deferred.Count > 0 && ItemGiver.InLevel)
            {
                foreach (var d in deferred) applyItem(d.Name, d.Sender, true);
                deferred.Clear();
                changed = true;
            }
            if (changed)
            {
                // Persist the cursor only up to the first item still waiting, so nothing is lost on quit.
                // (Items applied after a still-deferred one may be re-applied once after a restart; that's
                // preferable to losing the deferred item.)
                processedIndex = deferred.Count > 0 ? deferred.Min(d => d.Index) - 1 : Math.Max(processedIndex, highestSeen);
                SaveProcessedIndex();
            }
            while (true)
            {
                string source;
                lock (queueLock)
                {
                    if (pendingDeaths.Count == 0) break;
                    source = pendingDeaths.Dequeue();
                }
                onDeath(source);
            }
        }

        public int Count(string itemName) => ReceivedCounts.TryGetValue(itemName, out var c) ? c : 0;

        HashSet<long> activeLocations = new HashSet<long>();
        readonly HashSet<long> checkedLocations = new HashSet<long>();

        public bool IsLocationActive(long id) => Connected && activeLocations.Contains(id);

        public bool IsChecked(long id)
        {
            if (!Connected) return false;
            lock (checkedLocations) return checkedLocations.Contains(id);
        }

        public void Check(long id)
        {
            if (!Connected) return;
            lock (checkedLocations) checkedLocations.Add(id);
            Session.Locations.CompleteLocationChecks(id);
            CheckGoal();
        }

        public string DescribeLocation(long id) => GetScout(id)?.Display ?? "an Archipelago item";

        public void SendDeath()
        {
            deathLink?.SendDeathLink(new DeathLink(Session.Players.GetPlayerName(Session.ConnectionInfo.Slot)));
        }

        void CheckGoal()
        {
            IEnumerable<string> targets = Goal == "all_levels"
                ? Levels
                : Levels.Where(code => code == "E1M10" || code == "E2M10" || code == "E3M10");
            HashSet<long> done;
            lock (checkedLocations) done = new HashSet<long>(checkedLocations);
            foreach (var code in targets)
            {
                var lvl = LocationTable.LevelByCode[code];
                var loc = LocationTable.LevelComplete(lvl.Scene);
                if (loc == null || !done.Contains(loc.Id)) return;
            }
            Session.Socket.SendPacket(new StatusUpdatePacket { Status = ArchipelagoClientState.ClientGoal });
            Plugin.Log.LogInfo("Goal complete!");
        }

        // ---- persistence of the one-shot item cursor ---------------------------------------------
        string CursorFile => Path.Combine(BepInEx.Paths.ConfigPath, "DuskRando_items.txt");

        int LoadProcessedIndex()
        {
            try
            {
                foreach (var line in File.ReadAllLines(CursorFile))
                {
                    var parts = line.Split('=');
                    if (parts.Length == 2 && parts[0] == saveKey) return int.Parse(parts[1]);
                }
            }
            catch { /* no file yet */ }
            return -1;
        }

        void SaveProcessedIndex()
        {
            try
            {
                var lines = File.Exists(CursorFile)
                    ? File.ReadAllLines(CursorFile).Where(l => !l.StartsWith(saveKey + "=")).ToList()
                    : new List<string>();
                lines.Add($"{saveKey}={processedIndex}");
                File.WriteAllLines(CursorFile, lines.ToArray());
            }
            catch (Exception e) { Plugin.Log.LogWarning("Could not save item cursor: " + e.Message); }
        }
    }
}
