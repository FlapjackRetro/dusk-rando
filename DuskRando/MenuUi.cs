using System.Linq;
using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using DuskRando.Patches;
using Object = UnityEngine.Object;

namespace DuskRando
{
    /// <summary>
    /// Menu changes for issue #11. Every new button is a clone of a vanilla button next to it, so it uses the
    /// game's own sprites, fonts, colours, hover sounds and select/deselect triggers.
    ///
    /// Main menu (scene "Menu"): an ARCHIPELAGO button above CAMPAIGN. It goes through the game's own
    ///   level-select path (difficulty menu, then the episode map) for the seed's first episode.
    /// Pause menu (the same MAINMENU panel inside every level): a LEVEL SELECT button above CAMPAIGN that
    ///   leaves the level for the current episode's map. Only while connected.
    /// Episode maps (mapscene / mapscene2 / mapscene3): the BACK TO MAIN MENU button is cropped to half height
    ///   and an E1 / E2 / E3 row fills the other half, to switch maps. Episodes without any Access are greyed.
    /// </summary>
    public static class MenuUi
    {
        const float MenuStep = 90f; // vertical spacing of the vanilla main-menu buttons
        static readonly string[] MapSceneNames = { null, "mapscene", "mapscene2", "mapscene3" };

        public static void OnSceneLoaded(Scene scene)
        {
            var canvas = scene.GetRootGameObjects().FirstOrDefault(g => g.name == "Canvas");
            if (canvas == null) return;

            var main = canvas.transform.Find("MAINMENU");
            if (main != null)
            {
                if (scene.name == "Menu")
                    AddTopButton(main, "ARCHIPELAGO", OpenFromMainMenu);
                else if (Plugin.Client.Connected && LocationTable.LevelByScene.ContainsKey(scene.name))
                    AddTopButton(main, "LEVEL SELECT", () => LeaveToMap(EpisodeOf(scene.name)));
            }

            int ep = System.Array.IndexOf(MapSceneNames, scene.name);
            if (ep > 0 && Plugin.Client.Connected)
            {
                var panel = canvas.transform.Find("Panel") as RectTransform;
                if (panel != null)
                {
                    AddEpisodeRow(panel, ep);
                    MapKeysRow.Build(panel);
                }
            }
        }

        // ---- main / pause menu --------------------------------------------------------------------

        static void AddTopButton(Transform main, string label, UnityEngine.Events.UnityAction onClick)
        {
            var campaign = main.Find("ContinueButton") as RectTransform; // labelled CAMPAIGN in game
            if (campaign == null || main.Find("ArchipelagoButton") != null) return;

            // Make room: move the centred button stack down one step; the new button takes CAMPAIGN's old spot.
            // (Moving the stack down rather than adding above keeps clear of the DUSK logo.)
            var top = campaign.anchoredPosition;
            foreach (Transform t in main)
            {
                var child = t as RectTransform;
                if (child != null && child.anchorMin == new Vector2(0.5f, 0.5f) && child.anchorMax == new Vector2(0.5f, 0.5f))
                    child.anchoredPosition -= new Vector2(0, MenuStep);
            }

            var go = Object.Instantiate(campaign.gameObject, main, false);
            go.name = "ArchipelagoButton";
            go.transform.SetSiblingIndex(campaign.GetSiblingIndex());
            var rt = (RectTransform)go.transform;
            rt.anchoredPosition = top;
            // vanilla widths are ~47 px per character of the label (CAMPAIGN = 380)
            rt.sizeDelta = new Vector2(Mathf.Max(campaign.sizeDelta.x, 48f * label.Length), campaign.sizeDelta.y);
            SetLabel(go, label);

            var button = go.GetComponent<Button>();
            button.onClick = new Button.ButtonClickedEvent(); // drop the clone of CAMPAIGN's handler
            button.onClick.AddListener(onClick);

            // Controller/keyboard navigation is explicit in this menu: slot the new button in above CAMPAIGN.
            var campaignSel = campaign.GetComponent<Selectable>();
            var oldNav = campaignSel.navigation;
            foreach (var s in main.GetComponentsInChildren<Selectable>(true))
            {
                if (s == button || s.navigation.mode != Navigation.Mode.Explicit) continue;
                if (s.navigation.selectOnDown == campaignSel)
                {
                    var n = s.navigation; n.selectOnDown = button; s.navigation = n;
                }
            }
            var apNav = oldNav;
            apNav.selectOnDown = campaignSel;
            button.navigation = apNav;
            var cNav = oldNav;
            cNav.selectOnUp = button;
            campaignSel.navigation = cNav;
        }

        static void OpenFromMainMenu()
        {
            if (!Plugin.Client.Connected)
            {
                Plugin.ShowWindow("Connect to Archipelago first (F1), then press ARCHIPELAGO again.");
                return;
            }
            // Same as CAMPAIGN > LEVEL SELECT > Episode N: pick a difficulty, then the map loads.
            var menu = Object.FindObjectOfType<GameMenuButtonsScript>();
            if (menu == null) return;
            int ep = FirstEpisode();
            Traverse.Create(menu).Method(ep == 1 ? "levelep1press" : ep == 2 ? "levelep2press" : "levelep3press").GetValue();
        }

        static void LeaveToMap(int episode)
        {
            Time.timeScale = 1f; // the pause menu stops time
            AudioListener.pause = false;
            SceneManager.LoadScene(LevelGate.MapScenes[episode]);
        }

        static int EpisodeOf(string scene) =>
            LocationTable.LevelByScene.TryGetValue(scene, out var l) ? l.Episode : FirstEpisode();

        static int FirstEpisode()
        {
            for (int ep = 1; ep <= 3; ep++)
                if (EpisodeAvailable(ep)) return ep;
            return 1;
        }

        /// <summary>An episode is unlocked when the seed includes it and we hold Access to any of its levels.</summary>
        public static bool EpisodeAvailable(int ep) =>
            LocationTable.Levels.Any(l => l.Episode == ep && LevelGate.HasAccess(l));

        // ---- episode map ---------------------------------------------------------------------------

        static void AddEpisodeRow(RectTransform panel, int current)
        {
            var back = panel.Find("BackToMenuButton") as RectTransform;
            var list = panel.Find("Buttons") as RectTransform; // the level list above it
            if (back == null || panel.Find("APEpisodeArea") != null) return;

            // The gap between the level list and the back button, reused between every new edge.
            float panelHeight = panel.rect.height > 1f ? panel.rect.height : 1080f;
            float gap = list != null ? (list.anchorMin.y - back.anchorMax.y) * panelHeight : 10f;
            gap = Mathf.Clamp(gap, 6f, 24f);

            // A container that takes the back button's old rectangle exactly.
            var area = new GameObject("APEpisodeArea", typeof(RectTransform)).GetComponent<RectTransform>();
            area.SetParent(panel, false);
            area.SetSiblingIndex(back.GetSiblingIndex());
            area.anchorMin = back.anchorMin; area.anchorMax = back.anchorMax; area.pivot = back.pivot;
            area.anchoredPosition = back.anchoredPosition; area.sizeDelta = back.sizeDelta;

            // Bottom half: the cropped back button. Top half: three equal buttons, all separated by `gap`.
            back.SetParent(area, false);
            Place(back, 0f, 0f, 1f, 0.5f, 0f, 0f, 0f, -gap / 2f);
            SetNavigation(back, Navigation.Mode.Automatic);

            for (int i = 0; i < 3; i++)
            {
                int ep = i + 1;
                var go = Object.Instantiate(back.gameObject, area, false);
                go.name = "APEpisode" + ep;
                var rt = (RectTransform)go.transform;
                // left edge i*W/3 + i*g/3, right edge (i+1)*W/3 + (i-2)*g/3 -> width (W-2g)/3 and gaps of g
                Place(rt, i / 3f, 0.5f, (i + 1) / 3f, 1f, i * gap / 3f, gap / 2f, (i - 2) * gap / 3f, 0f);

                foreach (var s in go.GetComponents<FromMapToMenuScript>()) Object.DestroyImmediate(s);
                var prompt = go.transform.Find("MenuButtonPrompt"); // controller glyph belongs to BACK only
                if (prompt != null) Object.DestroyImmediate(prompt.gameObject);
                SetLabel(go, "E" + ep);

                var button = go.GetComponent<Button>();
                button.onClick = new Button.ButtonClickedEvent();
                bool available = EpisodeAvailable(ep);
                // the current episode stays fully drawn (highlighted text) but does nothing when pressed
                button.interactable = available || ep == current;
                if (ep != current) button.onClick.AddListener(() => SceneManager.LoadScene(LevelGate.MapScenes[ep]));
                SetNavigation(rt, Navigation.Mode.Automatic);

                var tmp = go.GetComponentInChildren<TextMeshProUGUI>(true);
                if (tmp != null)
                {
                    if (ep == current) tmp.color = new Color(1f, 0.82f, 0.25f); // the map you're on
                    else if (!available) tmp.color = new Color(tmp.color.r, tmp.color.g, tmp.color.b, 0.35f);
                }
            }
        }

        static void Place(RectTransform rt, float ax0, float ay0, float ax1, float ay1,
                          float left, float bottom, float right, float top)
        {
            rt.anchorMin = new Vector2(ax0, ay0);
            rt.anchorMax = new Vector2(ax1, ay1);
            rt.offsetMin = new Vector2(left, bottom);
            rt.offsetMax = new Vector2(right, top);
        }

        static void SetNavigation(Component c, Navigation.Mode mode)
        {
            var s = c.GetComponent<Selectable>();
            if (s == null) return;
            var n = s.navigation; n.mode = mode; s.navigation = n;
        }

        /// <summary>Set a cloned button's caption, removing the localisation component that would overwrite it.</summary>
        static void SetLabel(GameObject go, string text)
        {
            foreach (var loc in go.GetComponentsInChildren<UILocalizationScript>(true)) Object.DestroyImmediate(loc);
            foreach (var t in go.GetComponentsInChildren<Text>(true)) t.text = text;
            foreach (var t in go.GetComponentsInChildren<TextMeshProUGUI>(true)) t.text = text;
        }
    }
}
