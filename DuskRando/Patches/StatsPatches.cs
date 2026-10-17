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
    /// never saw which level had ended. The win screen is the reliable signal: LevelWinStuffScript.beststuff
    /// records the finished level's stats, and PersistScript.lastlevelnumber is that level's build index.
    /// </summary>
    [HarmonyPatch(typeof(LevelWinStuffScript), nameof(LevelWinStuffScript.beststuff))]
    static class LevelWinPatch
    {
        static void Postfix()
        {
            var persist = UnityEngine.Object.FindObjectOfType<PersistScript>();
            if (persist == null) return;
            var lvl = LevelGate.LevelForBuildIndex(persist.lastlevelnumber);
            if (lvl != null) Plugin.LevelCompleted(lvl.Scene, "win screen");
        }
    }
}
