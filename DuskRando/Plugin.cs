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
    [BepInPlugin(Guid, "DUSK Archipelago", "0.2.0")]
    public class Plugin : BaseUnityPlugin
    {
        public const string Guid = "flapjackretro.dusk.archipelago";
        public static ManualLogSource Log;
        public static ArchipelagoClient Client = new ArchipelagoClient();
        public static string PendingMessage;
        public static bool ReceivingDeath;

        ConfigEntry<string> host, slot, password;
        ConfigEntry<KeyCode> toggleKey;
        bool showWindow = true;
        Rect windowRect = new Rect(20, 20, 380, 190);
        string passwordText = "";

        // Scenes the game passes through after a level is finished (stats screen / story text / ending).
        static readonly string[] CompletionScenes = { "WinLevelScene", "TextScene", "TextScene2", "EndStoryScene", "CreditsScene" };

        void Awake()
        {
            Log = Logger;
            host = Config.Bind("Archipelago", "Server", "archipelago.gg:38281");
            slot = Config.Bind("Archipelago", "Slot", "Player");
            password = Config.Bind("Archipelago", "Password", "");
            toggleKey = Config.Bind("UI", "ToggleWindow", KeyCode.F1);
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

        void OnActiveSceneChanged(Scene from, Scene to)
        {
            if (!Client.Connected || string.IsNullOrEmpty(from.name)) return;
            if (!CompletionScenes.Contains(to.name)) return;
            var loc = LocationTable.LevelComplete(from.name);
            if (loc != null && Client.IsLocationActive(loc.Id))
            {
                Log.LogInfo($"Level complete: {from.name}");
                Client.Check(loc.Id);
            }
        }

        // ---- connection window ----------------------------------------------------------------
        static string Hint()
        {
            var scene = SceneManager.GetActiveScene().name;
            if (!Client.Connected)
                return scene == "Menu" ? "Connect here before starting a game." : null;
            if (scene == "Menu")
                return "To start: CAMPAIGN > NEW EPISODE, pick an episode.\n" +
                       "To replay or jump to unlocked levels: CAMPAIGN > LEVEL SELECT.\n" +
                       "Endless mode is not part of the randomizer.";
            if (scene.StartsWith("Endless") || scene == "QuakeconEndlessMode")
                return "Endless mode is not part of the randomizer: nothing here counts.";
            if (scene == "mapscene" || scene == "mapscene2" || scene == "mapscene3")
                return "Levels you have Access for are shown; the rest stay hidden.";
            return null;
        }

        void OnGUI()
        {
            if (!showWindow) return;
            windowRect = GUI.Window(0xD05C, windowRect, DrawWindow, "Archipelago (F1 to hide)");
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
            var hint = Hint();
            if (hint != null) GUILayout.Label(hint);
            GUI.DragWindow();
        }
    }
}
