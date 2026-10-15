using HarmonyLib;
using UnityEngine;

namespace DuskRando.Patches
{
    /// <summary>Marks a scene object as an Archipelago location (added on scene load by LevelTracker).</summary>
    public class ApLocation : MonoBehaviour
    {
        public long Id;
        public bool Sent;
        public bool Dressed; // ItemModels has given it the look of its real item
    }

    /// <summary>
    /// Every pickup in DUSK goes through PlayerPickupScript.TryPickupItem (see docs/reference). If the object is a
    /// randomized location we send the check instead of giving the vanilla item.
    /// </summary>
    [HarmonyPatch(typeof(PlayerPickupScript), nameof(PlayerPickupScript.TryPickupItem))]
    static class TryPickupItemPatch
    {
        static bool Prefix(PlayerPickupScript __instance, GameObject item, ref bool __result)
        {
            if (ItemGiver.Granting || item == null) return true;
            var loc = item.GetComponent<ApLocation>();
            if (loc == null) return true;
            if (!loc.Sent)
            {
                loc.Sent = true;
                Plugin.Client.Check(loc.Id);
                ItemGiver.Message("Found " + Plugin.Client.DescribeLocation(loc.Id));
                if (__instance.keysound != null)
                {
                    var audio = __instance.keysound.GetComponent<AudioSource>();
                    if (audio != null) audio.Play();
                }
            }
            var col = item.GetComponent<Collider>();
            if (col != null) col.enabled = false;
            Object.Destroy(item);
            __result = true;
            return false;
        }
    }

    /// <summary>Secret areas: TouchSecretScript (on the player) reacts to triggers tagged SecretTag.</summary>
    [HarmonyPatch(typeof(TouchSecretScript), "OnTriggerEnter")]
    static class SecretPatch
    {
        // __0: match the first argument by position; the parameter name in the game's build is not guaranteed.
        static void Prefix(Collider __0)
        {
            var other = __0;
            if (other == null || !other.CompareTag("SecretTag")) return;
            var loc = other.GetComponent<ApLocation>();
            if (loc == null || loc.Sent) return;
            loc.Sent = true;
            Plugin.Client.Check(loc.Id);
            ItemGiver.Message("Secret! Found " + Plugin.Client.DescribeLocation(loc.Id));
        }
    }

    /// <summary>
    /// Treasure chests spawn TreasureChestScript.myitem when opened and then set alreadyused. On scene load,
    /// LevelTracker swaps myitem for an inert placeholder; here we notice the chest being opened.
    /// </summary>
    [HarmonyPatch(typeof(TreasureChestScript), "Update")]
    static class TreasureChestPatch
    {
        static void Postfix(TreasureChestScript __instance)
        {
            if (__instance.alreadyused == 0) return;
            var loc = __instance.GetComponent<ApLocation>();
            if (loc == null || loc.Sent) return;
            loc.Sent = true;
            Plugin.Client.Check(loc.Id);
            ItemGiver.Message("Found " + Plugin.Client.DescribeLocation(loc.Id));
        }
    }

    /// <summary>DeathLink: notice the player dying.</summary>
    [HarmonyPatch(typeof(PlayerHealthManagement), "Update")]
    static class DeathPatch
    {
        static bool wasDead;

        static void Postfix(PlayerHealthManagement __instance)
        {
            if (__instance.iamdead && !wasDead && !Plugin.ReceivingDeath) Plugin.Client.SendDeath();
            if (!__instance.iamdead) Plugin.ReceivingDeath = false;
            wasDead = __instance.iamdead;
        }
    }
}
