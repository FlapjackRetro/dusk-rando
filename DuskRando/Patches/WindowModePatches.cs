using HarmonyLib;
using UnityEngine;

namespace DuskRando.Patches
{
    /// <summary>
    /// Issue #10: DUSK switches back to fullscreen on the main menu and on every level load.
    ///
    /// GameMenuButtonsScript.UpdateSettings re-applies config/dusk.ini on Start (every scene has one, in its
    /// pause-menu canvas) and after any settings change, including <c>Screen.fullScreen = ini "fullscreen"</c>.
    /// So a window made windowed with Alt+Enter (or launched windowed) is forced back to fullscreen.
    ///
    /// Fix: just before UpdateSettings runs, copy the window's current mode into the in-memory setting, so
    /// UpdateSettings re-applies what's already on screen. The game's own Fullscreen toggle in the settings
    /// menu still works: while PressFullscreenButton runs, the setting it just flipped is left alone.
    /// Turn off with [Display] KeepWindowMode = false in the mod's config.
    /// </summary>
    static class WindowMode
    {
        public static bool Enabled = true;
        public static bool UserToggling;
    }

    [HarmonyPatch(typeof(GameMenuButtonsScript), nameof(GameMenuButtonsScript.UpdateSettings))]
    static class KeepWindowModePatch
    {
        static void Prefix(GameMenuButtonsScript __instance)
        {
            if (!WindowMode.Enabled || WindowMode.UserToggling) return;
            try
            {
                int current = Screen.fullScreen ? 1 : 0;
                if (__instance.LoadConfigInt("fullscreen") != current)
                    __instance.SaveConfig("fullscreen", current); // in-memory ini data; the menu shows it too
            }
            catch (System.Exception e)
            {
                // e.g. settings not loaded yet; let the game behave as normal
                Plugin.Log.LogDebug("KeepWindowMode skipped: " + e.Message);
            }
        }
    }

    [HarmonyPatch(typeof(GameMenuButtonsScript), nameof(GameMenuButtonsScript.PressFullscreenButton))]
    static class FullscreenTogglePatch
    {
        static void Prefix() => WindowMode.UserToggling = true;
        static void Finalizer() => WindowMode.UserToggling = false; // runs even if the game's method throws
    }
}
