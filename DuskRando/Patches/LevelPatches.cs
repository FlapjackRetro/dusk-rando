using HarmonyLib;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace DuskRando.Patches
{
    /// <summary>
    /// Level access. Levels are opened by "<code> Access" items rather than vanilla progression.
    /// Every scene change goes through SceneManager, so any attempt to load a locked level (the game's own
    /// "next level" after finishing one, a save, or the level select) is redirected to that episode's map.
    /// </summary>
    static class LevelGate
    {
        // build indices of the per-episode map / level-select scenes
        public static readonly int[] MapScenes = { 21, 21, 33, 48 }; // [episode]

        public static bool HasAccess(LevelEntry lvl)
        {
            var c = Plugin.Client;
            if (!c.Connected) return true; // not playing AP: leave the game alone
            if (!c.Levels.Contains(lvl.Code)) return false;
            return c.Count(lvl.Code + " Access") > 0;
        }

        public static LevelEntry LevelForBuildIndex(int index)
        {
            var path = SceneUtility.GetScenePathByBuildIndex(index);
            var name = System.IO.Path.GetFileNameWithoutExtension(path);
            return name != null && LocationTable.LevelByScene.TryGetValue(name, out var l) ? l : null;
        }

        public static bool Redirect(ref int index)
        {
            var lvl = LevelForBuildIndex(index);
            if (lvl == null || HasAccess(lvl)) return false;
            Plugin.Log.LogInfo($"{lvl.Code} is locked, going to the map instead");
            index = MapScenes[lvl.Episode];
            Plugin.PendingMessage = $"{lvl.Code} {lvl.Name} is locked. Find \"{lvl.Code} Access\"!";
            return true;
        }

        public static bool Redirect(ref string name)
        {
            if (name == null || !LocationTable.LevelByScene.TryGetValue(name, out var lvl) || HasAccess(lvl))
                return false;
            int index = MapScenes[lvl.Episode];
            name = System.IO.Path.GetFileNameWithoutExtension(SceneUtility.GetScenePathByBuildIndex(index));
            Plugin.PendingMessage = $"{lvl.Code} {lvl.Name} is locked. Find \"{lvl.Code} Access\"!";
            return true;
        }
    }

    [HarmonyPatch(typeof(SceneManager), nameof(SceneManager.LoadScene), typeof(int), typeof(LoadSceneMode))]
    static class LoadSceneIntPatch { static void Prefix(ref int __0) => LevelGate.Redirect(ref __0); }

    [HarmonyPatch(typeof(SceneManager), nameof(SceneManager.LoadScene), typeof(string), typeof(LoadSceneMode))]
    static class LoadSceneStringPatch { static void Prefix(ref string __0) => LevelGate.Redirect(ref __0); }

    [HarmonyPatch(typeof(SceneManager), nameof(SceneManager.LoadSceneAsync), typeof(int), typeof(LoadSceneMode))]
    static class LoadSceneAsyncIntPatch { static void Prefix(ref int __0) => LevelGate.Redirect(ref __0); }

    [HarmonyPatch(typeof(SceneManager), nameof(SceneManager.LoadSceneAsync), typeof(string), typeof(LoadSceneMode))]
    static class LoadSceneAsyncStringPatch { static void Prefix(ref string __0) => LevelGate.Redirect(ref __0); }

    /// <summary>
    /// Map screen (CAMPAIGN > LEVEL SELECT). Vanilla MapNodeScript.Start hides every level that the save file
    /// hasn't beaten (ES2 "scores?tag=<n>levelbeaten"): canvas group alpha 0, no raycasts, map icon hidden.
    /// With Archipelago, what counts is "<code> Access", so show accessible levels and hide the others,
    /// whatever the save file says.
    /// </summary>
    [HarmonyPatch(typeof(MapNodeScript), "Start")]
    static class MapNodeStartPatch
    {
        static void Postfix(MapNodeScript __instance)
        {
            if (!Plugin.Client.Connected) return;
            var lvl = LevelGate.LevelForBuildIndex(__instance.mylevel);
            if (lvl == null) return;
            bool open = LevelGate.HasAccess(lvl);
            var t = Traverse.Create(__instance);
            var group = t.Field("_canvasGroup").GetValue<CanvasGroup>() ?? __instance.GetComponent<CanvasGroup>();
            if (group != null)
            {
                group.alpha = open ? 1f : 0f;
                group.interactable = open;
                group.blocksRaycasts = open;
            }
            var button = t.Field("_button").GetValue<Button>();
            if (button != null) button.interactable = open;
            var icon = t.Field("_mapIcon").GetValue<Component>();
            if (icon != null) icon.gameObject.SetActive(open);
        }
    }

    [HarmonyPatch(typeof(MapNodeScript), "clickity")]
    static class MapNodeClickPatch
    {
        static bool Prefix(MapNodeScript __instance)
        {
            var lvl = LevelGate.LevelForBuildIndex(__instance.mylevel);
            if (lvl == null || LevelGate.HasAccess(lvl)) return true;
            Plugin.Log.LogInfo($"Map: {lvl.Code} is locked");
            return false;
        }
    }
}

namespace DuskRando.Patches
{
    /// <summary>
    /// End of an episode (E1M10, E2M10): the story text scene (TextScene / TextScene2) offers Proceed or Return to
    /// Menu. Vanilla Proceed (NarrativeTextScript.Continue) stores the next episode's first level in
    /// PersistScript.leveltoload and loads LogoScene, which plays the next episode's intro movie and then drops
    /// the player into that level. With Archipelago, Proceed goes back to the level select map of the episode
    /// that was just finished instead, skipping the movie.
    /// </summary>
    [HarmonyPatch(typeof(NarrativeTextScript), nameof(NarrativeTextScript.Continue))]
    static class EpisodeEndProceedPatch
    {
        static bool Prefix(NarrativeTextScript __instance)
        {
            if (!Plugin.Client.Connected) return true;
            var next = NextLevel(Traverse.Create(__instance).Field("levelload").GetValue());
            int episode = next == null ? 1 : next.Episode > 1 ? next.Episode - 1 : next.Episode;
            if (!MenuUi.EpisodeAvailable(episode) && next != null && MenuUi.EpisodeAvailable(next.Episode))
                episode = next.Episode;
            Plugin.Log.LogInfo($"Episode end: Proceed goes to the episode {episode} map (vanilla would load " +
                               $"{next?.Code ?? "?"} after its intro movie)");
            SceneManager.LoadScene(LevelGate.MapScenes[episode]);
            return false;
        }

        static LevelEntry NextLevel(object levelload)
        {
            if (levelload is int index) return LevelGate.LevelForBuildIndex(index);
            if (levelload is string name && LocationTable.LevelByScene.TryGetValue(name, out var l)) return l;
            return null;
        }
    }
}
