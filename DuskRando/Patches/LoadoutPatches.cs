using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace DuskRando.Patches
{
    /// <summary>
    /// Issue #9: the map screen's loadout picker ("Stuff and stuff" LoadoutStuffScript + one LoadoutEntryScript
    /// per weapon row in Canvas/ConfirmBox) let you tick any weapon, so weapon items didn't matter.
    ///
    /// While connected to a seed that randomizes weapons:
    /// - a row's checkmark follows what you've received and can't be toggled;
    /// - "+" only adds ammo to weapons you have;
    /// - MAX fills ammo for the weapons you have (vanilla also ticks every weapon);
    /// - Reset zeroes ammo for the weapons you have, and leaves the checkmarks alone.
    /// Otherwise the picker behaves as in the vanilla game.
    /// </summary>
    static class Loadout
    {
        // Loadout row (GameObject name under Canvas/ConfirmBox) -> item and how many copies are needed.
        static readonly Dictionary<string, KeyValuePair<string, int>> Rows = new Dictionary<string, KeyValuePair<string, int>>
        {
            { "Pistol", Need("Progressive Pistol", 1) }, { "x2pistols", Need("Progressive Pistol", 2) },
            { "Shotgun", Need("Progressive Shotgun", 1) }, { "x2shotguns", Need("Progressive Shotgun", 2) },
            { "Super Shotgun", Need("Super Shotgun", 1) }, { "Assault Rifle", Need("Assault Rifle", 1) },
            { "Hunting Rifle", Need("Hunting Rifle", 1) }, { "Crossbow", Need("Crossbow", 1) },
            { "Mortar", Need("Mortar", 1) }, { "Riveter", Need("Riveter", 1) }, { "Sword", Need("Sword", 1) },
        };

        static KeyValuePair<string, int> Need(string item, int count) => new KeyValuePair<string, int>(item, count);

        public static bool Active => Plugin.Client.Connected && Plugin.Client.Categories.Contains("weapons");

        /// <summary>Has the player received the weapon this row stands for? Unknown rows count as owned.</summary>
        public static bool Owned(LoadoutEntryScript row)
        {
            if (!Rows.TryGetValue(row.gameObject.name, out var need)) return true;
            return Plugin.Client.Count(need.Key) >= need.Value;
        }
    }

    [HarmonyPatch(typeof(LoadoutEntryScript), "Update")]
    static class LoadoutRowStatePatch
    {
        // Before Update draws the row (checkmark colour, row alpha), make haveweapon match what's been received.
        static void Prefix(LoadoutEntryScript __instance)
        {
            if (!Loadout.Active) return;
            bool owned = Loadout.Owned(__instance);
            __instance.haveweapon = owned;
            if (!owned) __instance.ammo = 0;
        }
    }

    [HarmonyPatch(typeof(LoadoutEntryScript), nameof(LoadoutEntryScript.weaponbutton))]
    static class LoadoutRowTogglePatch
    {
        static bool Prefix() => !Loadout.Active; // checkmarks aren't toggleable during a seed
    }

    [HarmonyPatch(typeof(LoadoutEntryScript), nameof(LoadoutEntryScript.plus))]
    static class LoadoutRowPlusPatch
    {
        static bool Prefix(LoadoutEntryScript __instance) => !Loadout.Active || Loadout.Owned(__instance);
    }

    [HarmonyPatch(typeof(LoadoutEntryScript), nameof(LoadoutEntryScript.Reset))]
    static class LoadoutRowResetPatch
    {
        static bool Prefix(LoadoutEntryScript __instance)
        {
            if (!Loadout.Active) return true;
            __instance.ammo = 0; // vanilla also unticks the weapon
            return false;
        }
    }

    [HarmonyPatch(typeof(LoadoutEntryScript), nameof(LoadoutEntryScript.Max))]
    static class LoadoutRowMaxPatch
    {
        static bool Prefix(LoadoutEntryScript __instance)
        {
            if (!Loadout.Active) return true;
            bool owned = Loadout.Owned(__instance);
            __instance.haveweapon = owned;
            __instance.ammo = owned ? __instance.max : 0;
            return false;
        }
    }

    [HarmonyPatch(typeof(LoadoutStuffScript), nameof(LoadoutStuffScript.GetAll))]
    static class LoadoutMaxPatch
    {
        static bool Prefix(LoadoutStuffScript __instance)
        {
            if (!Loadout.Active) return true;
            // Every LoadoutEntryScript field on the script (pistolscript, shotgunscript, ...).
            foreach (var field in AccessTools.GetDeclaredFields(typeof(LoadoutStuffScript)))
            {
                if (field.FieldType != typeof(LoadoutEntryScript)) continue;
                var row = field.GetValue(__instance) as LoadoutEntryScript;
                if (row == null) continue;
                bool owned = Loadout.Owned(row);
                row.haveweapon = owned;
                row.ammo = owned ? row.max : 0;
            }
            return false;
        }
    }
}
