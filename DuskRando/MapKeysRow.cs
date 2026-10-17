using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;
using DuskRando.Patches;
using Object = UnityEngine.Object;

namespace DuskRando
{
    /// <summary>
    /// Level map: a KEYS row under TIME / KILLS / SECRETS in the stats box, showing the hovered level's keys.
    /// Keys the level has are drawn in their colour once received, and dark until then. A level without keys
    /// reads "NONE". Only shown while connected to a seed that randomizes keys.
    ///
    /// The stats box (Canvas/Panel/StatsPanel/Stats) is a VerticalLayoutGroup that sizes its rows to fill it.
    /// The new row is a clone of the SECRETS row, so it uses the same font, shadow and label/value split. The
    /// box is stretched down toward the bottom of the panel so the four rows stay close to their old height.
    /// MapNodeScript.mouseover fills in the stats for the hovered level, so a postfix there updates the keys.
    /// </summary>
    public static class MapKeysRow
    {
        static readonly string[] Order = { "Blue Key", "Yellow Key", "Red Key" };
        static readonly Dictionary<string, Color> Colors = new Dictionary<string, Color>
        {
            { "Blue Key", new Color(0.25f, 0.45f, 1f) },
            { "Yellow Key", new Color(1f, 0.85f, 0.15f) },
            { "Red Key", new Color(0.9f, 0.12f, 0.1f) },
        };
        // Not yet received: the same colour, darkened and half see-through, so the level's keys are still visible.
        const float MissingShade = 0.35f, MissingAlpha = 0.6f;

        static Text valueText;
        static Image[] icons;
        static Sprite keySprite;

        public static void Build(RectTransform panel)
        {
            valueText = null;
            icons = null;
            if (!Plugin.Client.Categories.Contains("keys")) return;
            var stats = panel.Find("StatsPanel/Stats") as RectTransform;
            var secrets = stats != null ? stats.Find("Secrets") : null;
            if (secrets == null || stats.Find("Keys") != null) return;

            // Four rows instead of three: grow the box down most of the way to the panel's bottom edge.
            stats.anchorMin = new Vector2(stats.anchorMin.x, Mathf.Min(stats.anchorMin.y, 0.03f));

            var row = Object.Instantiate(secrets.gameObject, stats, false);
            row.name = "Keys";
            row.transform.SetSiblingIndex(secrets.GetSiblingIndex() + 1);
            foreach (var loc in row.GetComponentsInChildren<UILocalizationScript>(true)) Object.DestroyImmediate(loc);

            var label = row.transform.Find("SecretsLabel");
            if (label != null) { label.name = "KeysLabel"; label.GetComponent<Text>().text = "KEYS:"; }
            var value = row.transform.Find("BestSecrets");
            if (value == null) return;
            value.name = "KeyIcons";
            valueText = value.GetComponent<Text>();
            valueText.text = "";

            if (keySprite == null) keySprite = MakeKeySprite();
            icons = new Image[3];
            for (int i = 0; i < 3; i++)
            {
                var go = new GameObject("Key" + i, typeof(RectTransform));
                var rt = (RectTransform)go.transform;
                rt.SetParent(value, false);
                rt.anchorMin = new Vector2(i / 3f, 0.2f);
                rt.anchorMax = new Vector2((i + 1) / 3f, 0.8f);
                rt.offsetMin = new Vector2(4f, 0f);
                rt.offsetMax = new Vector2(-4f, 0f);
                var img = go.AddComponent<Image>();
                img.sprite = keySprite;
                img.preserveAspect = true;
                img.raycastTarget = false;
                go.AddComponent<Shadow>().effectDistance = new Vector2(2f, -2f); // like the row's text
                go.SetActive(false);
                icons[i] = img;
            }
        }

        public static void Show(LevelEntry lvl)
        {
            if (icons == null || valueText == null) return;
            foreach (var i in icons) i.gameObject.SetActive(false);
            if (lvl == null) { valueText.text = ""; return; }

            var keys = new List<string>();
            foreach (var k in Order) if (lvl.Keys.Contains(k)) keys.Add(k);
            if (keys.Count == 0) { valueText.text = "NONE"; return; }
            valueText.text = "";

            // Centre the icons in the three slots: one key in the middle slot, two keys either side of it.
            int start = keys.Count == 3 ? 0 : keys.Count == 2 ? 0 : 1;
            for (int n = 0; n < keys.Count; n++)
            {
                var img = icons[start + n];
                if (keys.Count == 2)
                {
                    var rt = img.rectTransform; // two keys: halves instead of thirds
                    rt.anchorMin = new Vector2(n / 2f + 0.08f, 0.2f);
                    rt.anchorMax = new Vector2((n + 1) / 2f - 0.08f, 0.8f);
                }
                else
                {
                    int slot = start + n;
                    img.rectTransform.anchorMin = new Vector2(slot / 3f, 0.2f);
                    img.rectTransform.anchorMax = new Vector2((slot + 1) / 3f, 0.8f);
                }
                var c = Colors[keys[n]];
                bool have = Plugin.Client.Count($"{lvl.Code} {keys[n]}") > 0;
                img.color = have ? c : new Color(c.r * MissingShade, c.g * MissingShade, c.b * MissingShade, MissingAlpha);
                img.gameObject.SetActive(true);
            }
        }

        /// <summary>A small pixel-art key (bow, shaft, two teeth), white so Image.color tints it.</summary>
        static Sprite MakeKeySprite()
        {
            string[] rows =
            {
                "..XXX.............",
                ".XXXXX............",
                "XXX.XXXXXXXXXXXXXX",
                "XX...XXXXXXXXXXXXX",
                "XXX.XXX.......X.XX",
                ".XXXXX........X.XX",
                "..XXX.............",
            };
            int w = rows[0].Length, h = rows.Length;
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                    tex.SetPixel(x, h - 1 - y, rows[y][x] == 'X' ? Color.white : new Color(1, 1, 1, 0));
            tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 16f);
        }
    }

    [HarmonyPatch(typeof(MapNodeScript), "mouseover")]
    static class MapKeysHoverPatch
    {
        static void Postfix(MapNodeScript __instance)
        {
            if (!Plugin.Client.Connected) return;
            MapKeysRow.Show(LevelGate.LevelForBuildIndex(__instance.mylevel));
        }
    }
}
