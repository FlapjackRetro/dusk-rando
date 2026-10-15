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

    /// <summary>Map screen: show every level we have access to as selectable, and refuse locked ones.</summary>
    [HarmonyPatch(typeof(MapNodeScript), "Start")]
    static class MapNodeStartPatch
    {
        static void Postfix(MapNodeScript __instance)
        {
            if (!Plugin.Client.Connected) return;
            var lvl = LevelGate.LevelForBuildIndex(__instance.mylevel);
            if (lvl == null) return;
            bool open = LevelGate.HasAccess(lvl);
            var button = Traverse.Create(__instance).Field("_button").GetValue<Button>();
            if (button != null) button.interactable = open;
            var group = Traverse.Create(__instance).Field("_canvasGroup").GetValue<CanvasGroup>();
            if (group != null) group.alpha = open ? 1f : 0.35f;
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
