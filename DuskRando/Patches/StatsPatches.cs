using System;
using System.IO;
using HarmonyLib;
using UnityEngine;

namespace DuskRando.Patches
{
    /// <summary>
    /// Issue #15: per-level stats (best time, kills, secrets, awards, "beaten" flags) carried over from earlier
    /// playthroughs into a new seed.
    ///
    /// DUSK keeps them in one Easy Save 2 file, <c>Dusk/config/scores</c>, addressed as
    /// <c>Application.dataPath + "/../config/scores?tag=&lt;level&gt;&lt;stat&gt;"</c>. The map screen reads it
    /// (MapNodeScript), the win screen writes it (LevelWinStuffScript.beststuff) and StatScript marks a level
    /// beaten on entry. Every ES2 call turns that path into an ES2Settings, either with
    /// <c>new ES2Settings(path)</c> or <c>settings.Clone(path)</c>, so rewriting the path there redirects them all.
    ///
    /// While a seed is active, <c>config/scores</c> becomes <c>config/archipelago/scores_&lt;seed&gt;_&lt;slot&gt;</c>:
    /// a new seed starts with clean stats, the same seed keeps its stats across sessions, and the vanilla file
    /// is never touched.
    /// </summary>
    static class SeedStats
    {
        const string VanillaPart = "/config/scores";

        public static string FileFor(string seedKey) => "scores_" + seedKey;

        public static string Directory =>
            Path.GetFullPath(Path.Combine(Application.dataPath, Path.Combine("..", Path.Combine("config", "archipelago"))));

        public static void Rewrite(ref string identifier)
        {
            var key = Plugin.Client.SeedKey;
            if (key == null || identifier == null) return;
            // Normalise separators for the match only; the game always builds this path with '/'.
            int at = identifier.Replace('\\', '/').IndexOf(VanillaPart + "?", StringComparison.OrdinalIgnoreCase);
            if (at < 0) return;
            identifier = identifier.Substring(0, at) + "/config/archipelago/" + FileFor(key) +
                         identifier.Substring(at + VanillaPart.Length);
        }
    }

    [HarmonyPatch(typeof(ES2Settings), MethodType.Constructor, typeof(string))]
    static class ES2SettingsCtorPatch
    {
        static void Prefix(ref string __0) => SeedStats.Rewrite(ref __0);
    }

    [HarmonyPatch(typeof(ES2Settings), nameof(ES2Settings.Clone), typeof(string))]
    static class ES2SettingsClonePatch
    {
        static void Prefix(ref string __0) => SeedStats.Rewrite(ref __0);
    }

    /// <summary>
    /// Issue #8: "Level Complete" wasn't sent after finishing E1M1. Unity passes an empty scene as the "from"
    /// argument of SceneManager.activeSceneChanged once the old scene is unloaded, so the scene-change check
    /// never saw which level had ended. The win screen (LevelWinStuffScript.beststuff) is a second signal.
    ///
    /// Issue #52: the level it credits is the one the mod saw being played (Plugin.PlayedLevelScene), not
    /// PersistScript.lastlevelnumber. An alternate exit (EndLevelTrigger.altlevel / EndLevelButton
    /// altleveltoload) ends the level with lastlevelnumber = target - 1, so that the win screen's "next level"
    /// (lastlevelnumber + 1) is the target. E3M4's secret exit to E3MS (47) therefore leaves 46 = E3M10, and the
    /// old code completed E3M10. Same for E2M4 -> E2MS (E2M10), E1MS/E2MS/E3MS -> back (E1M2/E2M4/E3M4).
    /// </summary>
    [HarmonyPatch(typeof(LevelWinStuffScript), nameof(LevelWinStuffScript.beststuff))]
    static class LevelWinPatch
    {
        static void Postfix()
        {
            var played = Plugin.PlayedLevelScene;
            if (played != null) Plugin.LevelCompleted(played, "win screen");
        }
    }
}
