using System.Linq;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using DuskRando.Patches;
using HarmonyLib;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace DuskRando
{
    [BepInPlugin(Guid, "DUSK Archipelago", PluginInfo.Version)]
    public class Plugin : BaseUnityPlugin
    {
        public const string Guid = "flapjackretro.dusk.archipelago";
        public static ManualLogSource Log;
        public static ArchipelagoClient Client = new ArchipelagoClient();
        public static string PendingMessage;
        public static bool ReceivingDeath;
        static Plugin instance;
        static string windowNote;

        /// <summary>Open the connection window, optionally with a one-line note under the status.</summary>
        public static void ShowWindow(string note = null)
        {
            if (instance == null) return;
            instance.showWindow = true;
            windowNote = note;
        }

        ConfigEntry<string> host, slot, password;
        ConfigEntry<KeyCode> toggleKey;
        bool showWindow = true;
        Rect windowRect = new Rect(20, 20, 380, 0);
        GUIStyle versionStyle;
        string passwordText = "";

        // Scenes the game passes through after a level is finished (stats screen / story text / ending).
        static readonly string[] CompletionScenes = { "WinLevelScene", "TextScene", "TextScene2", "EndStoryScene", "CreditsScene" };

        void Awake()
        {
            Log = Logger;
            instance = this;
            host = Config.Bind("Archipelago", "Server", "archipelago.gg:38281");
            slot = Config.Bind("Archipelago", "Slot", "Player");
            password = Config.Bind("Archipelago", "Password", "");
            ArchipelagoClient.UseCompression = Config.Bind("Archipelago", "UseCompression", true,
                "Use a compressed (permessage-deflate) websocket connection, as Archipelago recommends. " +
                "If it fails, the mod falls back to an uncompressed connection automatically.").Value;
            toggleKey = Config.Bind("UI", "ToggleWindow", KeyCode.F1);
            WindowMode.Enabled = Config.Bind("Display", "KeepWindowMode", true,
                "Stop DUSK from switching back to fullscreen on the menu and on every level load. " +
                "The game's own Fullscreen setting still works.").Value;
            passwordText = password.Value;
            LocationTable.Load();
            ItemModels.Init();
            new Harmony(Guid).PatchAll();
            SceneManager.sceneLoaded += OnSceneLoaded;
            SceneManager.activeSceneChanged += OnActiveSceneChanged;
        }

        void Update()
        {
            if (Input.GetKeyDown(toggleKey.Value)) showWindow = !showWindow;
            if (Client.Connected)
                Client.Pump(ItemGiver.Apply, OnDeathLink);
            if (Client.ScoutsArrived)
            {
                Client.ScoutsArrived = false;
                DressAll();
            }
            if (PendingMessage != null && ItemGiver.InLevel)
            {
                ItemGiver.Message(PendingMessage);
                PendingMessage = null;
            }
        }

        void OnDeathLink(string source)
        {
            var hp = FindObjectOfType<PlayerHealthManagement>();
            if (hp == null || hp.iamdead) return;
            ReceivingDeath = true;
            ItemGiver.Message($"DeathLink from {source}");
            hp.myhealth = 0;
            hp.myarmor = 0;
        }

        // ---- level lifecycle ------------------------------------------------------------------
        void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            try { MenuUi.OnSceneLoaded(scene); }
            catch (System.Exception e) { Log.LogError("Menu changes failed: " + e); }
            if (!Client.Connected || !LocationTable.LevelByScene.ContainsKey(scene.name)) return;
            ItemModels.Harvest(); // before anything is destroyed or re-dressed
            int marked = 0, removed = 0;
            foreach (var save in FindObjectsOfType<SavePickupScript>())
                Mark(scene.name, save.gameObject, ref marked, ref removed);
            foreach (var chest in FindObjectsOfType<TreasureChestScript>())
            {
                if (!Mark(scene.name, chest.gameObject, ref marked, ref removed, destroyIfChecked: false)) continue;
                // Opening the chest still plays out, but spawns nothing.
                var placeholder = new GameObject("AP Chest Placeholder");
                placeholder.SetActive(false);
                chest.myitem = placeholder;
            }
            Log.LogInfo($"{scene.name}: {marked} randomized pickups, {removed} already collected");
            DressAll();
            // Weapons/keys: give them a frame so SelectionScript.Start has run.
            StartCoroutine(ApplyStateNextFrame());
        }

        static void DressAll()
        {
            foreach (var loc in FindObjectsOfType<ApLocation>()) ItemModels.Apply(loc);
        }

        System.Collections.IEnumerator ApplyStateNextFrame()
        {
            yield return null;
            yield return null;
            ItemGiver.ApplyPersistentState();
        }

        bool Mark(string scene, GameObject go, ref int marked, ref int removed, bool destroyIfChecked = true)
        {
            var entry = LocationTable.Match(scene, go);
            if (entry == null || !Client.IsLocationActive(entry.Id)) return false;
            var marker = go.AddComponent<ApLocation>();
            marker.Id = entry.Id;
            if (Client.IsChecked(entry.Id))
            {
                marker.Sent = true;
                removed++;
                // Collected pickups disappear. Secret triggers stay so the game's secret counter still works.
                if (destroyIfChecked && !go.CompareTag("SecretTag")) Destroy(go);
                return true;
            }
            marked++;
            return true;
        }

        static string lastLevelScene; // Unity's activeSceneChanged gives an empty "from" scene (#8)

        /// <summary>
        /// The level being played or just finished: set when a level loads, kept through the win/story scenes that
        /// follow it, cleared by any other scene (menu, map, loading screen). Used by the win screen (#52).
        /// </summary>
        public static string PlayedLevelScene { get; private set; }

        void OnActiveSceneChanged(Scene from, Scene to)
        {
            Client.ReportScene(to.name);
            if (LocationTable.LevelByScene.ContainsKey(to.name)) { lastLevelScene = PlayedLevelScene = to.name; return; }
            if (!CompletionScenes.Contains(to.name)) PlayedLevelScene = null;
            var finished = !string.IsNullOrEmpty(from.name) ? from.name : lastLevelScene;
            // Only a direct jump from a level to a win/story/credits scene counts. Anything else (menu, map,
            // loading screen) means the level was left, so forget it; an episode's intro TextScene from the
            // menu must not complete whatever level was played last.
            lastLevelScene = null;
            if (CompletionScenes.Contains(to.name) && finished != null && LocationTable.LevelByScene.ContainsKey(finished))
                LevelCompleted(finished, "scene change to " + to.name);
        }

        /// <summary>Send a level's "Level Complete" check (idempotent).</summary>
        public static void LevelCompleted(string scene, string how)
        {
            if (!Client.Connected || scene == null) return;
            var loc = LocationTable.LevelComplete(scene);
            if (loc == null || !Client.IsLocationActive(loc.Id) || Client.IsChecked(loc.Id)) return;
            Log.LogInfo($"Level complete: {scene} ({how})");
            Client.Check(loc.Id);
        }

        // ---- connection window ----------------------------------------------------------------
        static string Hint()
        {
            var scene = SceneManager.GetActiveScene().name;
            if (!Client.Connected)
                return scene == "Menu" ? "Connect here before starting a game." : null;
            if (scene == "Menu")
                return "To play: press ARCHIPELAGO, pick a difficulty, then pick a level on the map.\n" +
                       "In a level, the pause menu's LEVEL SELECT takes you back to the map.";
            if (scene.StartsWith("Endless") || scene == "QuakeconEndlessMode")
                return "Endless mode is not part of the randomizer: nothing here counts.";
            if (scene == "mapscene" || scene == "mapscene2" || scene == "mapscene3")
                return "Levels you have Access for are shown; E1 / E2 / E3 switch episodes.";
            return null;
        }

        void OnGUI()
        {
            if (!showWindow) return;
            // Auto-sized to its contents (height 0 each frame, so it also shrinks when a note goes away).
            windowRect = GUILayout.Window(0xD05C, new Rect(windowRect.x, windowRect.y, 380, 0), DrawWindow,
                "Archipelago (F1 to hide)", GUILayout.Width(380));
        }

        void DrawWindow(int id)
        {
            GUILayout.Label("Server");
            host.Value = GUILayout.TextField(host.Value);
            GUILayout.Label("Slot / Password");
            GUILayout.BeginHorizontal();
            slot.Value = GUILayout.TextField(slot.Value, GUILayout.Width(160));
            passwordText = GUILayout.PasswordField(passwordText, '*');
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            if (!Client.Connected && GUILayout.Button("Connect"))
            {
                password.Value = passwordText;
                Client.Connect(host.Value, slot.Value, passwordText);
            }
            if (Client.Connected && GUILayout.Button("Disconnect")) Client.Disconnect();
            GUILayout.EndHorizontal();
            GUILayout.Label(Client.Status);
            if (windowNote != null && !Client.Connected) GUILayout.Label(windowNote);
            var hint = Hint();
            if (hint != null) GUILayout.Label(hint);
            // Issue #29: mod version, small, at the very bottom (for bug reports).
            if (versionStyle == null)
                versionStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 10,
                    alignment = TextAnchor.LowerRight,
                    normal = { textColor = new Color(0.7f, 0.7f, 0.7f) },
                };
            GUILayout.Label("DuskRando v" + PluginInfo.Version, versionStyle);
            GUI.DragWindow();
        }
    }
}
