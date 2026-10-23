using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace DuskRando
{
    /// <summary>
    /// Issue #53: level map stats box, a CHECKS row showing how many of the hovered level's checks in this seed
    /// have been found ("12 / 31"), green once all of them are done. It goes under KEYS (or under SECRETS when the
    /// seed doesn't randomize keys). Built like MapKeysRow: a clone of the SECRETS row, filled from the same
    /// MapNodeScript.mouseover postfix. "Checks" means this seed's locations in that level, Level Complete included.
    /// </summary>
    public static class MapChecksRow
    {
        static readonly Color Done = new Color(0.35f, 0.9f, 0.35f);
        static Text valueText;
        static Color normalColor;

        public static void Build(RectTransform panel)
        {
            valueText = null;
            var stats = panel.Find("StatsPanel/Stats") as RectTransform;
            var secrets = stats != null ? stats.Find("Secrets") : null;
            if (secrets == null || stats.Find("Checks") != null) return;

            // One more row: use the rest of the panel's height (MapKeysRow already took most of it).
            stats.anchorMin = new Vector2(stats.anchorMin.x, Mathf.Min(stats.anchorMin.y, 0.01f));

            var row = Object.Instantiate(secrets.gameObject, stats, false);
            row.name = "Checks";
            var above = stats.Find("Keys") ?? secrets;
            row.transform.SetSiblingIndex(above.GetSiblingIndex() + 1);
            foreach (var loc in row.GetComponentsInChildren<UILocalizationScript>(true)) Object.DestroyImmediate(loc);

            var label = row.transform.Find("SecretsLabel");
            if (label != null) { label.name = "ChecksLabel"; label.GetComponent<Text>().text = "CHECKS:"; }
            var value = row.transform.Find("BestSecrets");
            if (value == null) return;
            value.name = "CheckCount";
            valueText = value.GetComponent<Text>();
            normalColor = valueText.color;
            valueText.text = "";
        }

        public static void Show(LevelEntry lvl)
        {
            if (valueText == null) return;
            valueText.color = normalColor;
            if (lvl == null) { valueText.text = ""; return; }
            int total = 0, found = 0;
            foreach (var loc in LocationTable.InScene(lvl.Scene))
            {
                if (!Plugin.Client.IsLocationActive(loc.Id)) continue;
                total++;
                if (Plugin.Client.IsChecked(loc.Id)) found++;
            }
            valueText.text = $"{found} / {total}";
            if (total > 0 && found == total) valueText.color = Done;
        }
    }
}
