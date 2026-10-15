using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace DuskRando
{
    /// <summary>
    /// Applies received Archipelago items to the game. Wherever possible it builds a throwaway pickup object and
    /// feeds it to the game's own PlayerPickupScript.TryPickupItem, so messages, sounds and edge cases (dual pistols
    /// on the second pistol, ammo caps...) behave exactly like vanilla.
    /// </summary>
    public static class ItemGiver
    {
        /// <summary>Set while we hand the game a synthetic pickup, so our TryPickupItem patch lets it through.</summary>
        public static bool Granting;

        class WeaponDef
        {
            public int Index, Ammo; public string Message, Tag;
            public WeaponDef(int index, string message, int ammo, string tag) { Index = index; Message = message; Ammo = ammo; Tag = tag; }
        }

        class AmmoDef
        {
            public int Index, Amount; public string Message;
            public AmmoDef(int index, int amount, string message) { Index = index; Amount = amount; Message = message; }
        }

        class HealthDef
        {
            public float Health, Armor; public string Message; public bool DoubleHealth, DoubleArmor;
            public HealthDef(float health, float armor, string message, bool doubleHealth, bool doubleArmor)
            { Health = health; Armor = armor; Message = message; DoubleHealth = doubleHealth; DoubleArmor = doubleArmor; }
        }

        // Values copied from the vanilla pickups (see data/raw_pickups.json). Index = WeaponPickupScript.weaponcontent.
        static readonly Dictionary<string, WeaponDef> Weapons = new Dictionary<string, WeaponDef>
        {
            { "Progressive Pistol", new WeaponDef(1, "PICKUP_PISTOL", 12, "Weapon Pickup") },
            { "Progressive Shotgun", new WeaponDef(2, "PICKUP_SHOTGUN", 6, "Weapon Pickup") },
            { "Super Shotgun", new WeaponDef(3, "PICKUP_SUPER_SHOTGUN", 6, "SuperShotgunTag") },
            { "Assault Rifle", new WeaponDef(4, "PICKUP_ASSAULT", 24, "Weapon Pickup") },
            { "Hunting Rifle", new WeaponDef(5, "PICKUP_RIFLE", 7, "Weapon Pickup") },
            { "Crossbow", new WeaponDef(6, "PICKUP_CROSSBOW", 10, "Weapon Pickup") },
            { "Mortar", new WeaponDef(7, "PICKUP_MORTAR", 10, "Weapon Pickup") },
            { "Riveter", new WeaponDef(8, "PICKUP_RIVETER", 5, "Weapon Pickup") },
        };

        static readonly Dictionary<string, AmmoDef> Ammo = new Dictionary<string, AmmoDef>
        {
            { "Pistol Bullet", new AmmoDef(1, 1, "PICKUP_BULLETS_1") },
            { "Pistol Clip", new AmmoDef(1, 12, "PICKUP_BULLETS_12") },
            { "Box of Pistol Bullets", new AmmoDef(1, 36, "PICKUP_BULLETS_36") },
            { "Shotgun Shell", new AmmoDef(3, 1, "PICKUP_SHELLS_1") },
            { "Box of Shotgun Shells", new AmmoDef(3, 12, "PICKUP_SHELLS_12") },
            { "Assault Rifle Magazine", new AmmoDef(4, 24, "PICKUP_ASSAULT_BULLETS_24") },
            { "Hunting Rifle Bullet", new AmmoDef(5, 1, "PICKUP_RIFLE_BULLETS_1") },
            { "Box of Hunting Rifle Bullets", new AmmoDef(5, 5, "PICKUP_RIFLE_BULLETS_5") },
            { "Crossbow Bolts", new AmmoDef(6, 10, "PICKUP_CROSSBOW_10") },
            { "Mortar Grenade", new AmmoDef(7, 1, "PICKUP_GRENADE_1") },
            { "Box of Mortar Grenades", new AmmoDef(7, 6, "PICKUP_GRENADES_6") },
            { "Rivets", new AmmoDef(8, 1, "PICKUP_RIVET") },
        };

        static readonly Dictionary<string, HealthDef> Health = new Dictionary<string, HealthDef>
        {
            { "Medical Kit", new HealthDef(15, 0, "PICKUP_HEALTH_PACK", false, false) },
            { "Small Medical Kit", new HealthDef(7, 0, "PICKUP_HEALTH_SMALL", false, false) },
            { "Magic Potion", new HealthDef(1, 0, "PICKUP_HEALTH_BONUS", true, false) },
            { "Gold Coin", new HealthDef(0, 1, "PICKUP_ARMOR_BONUS", false, true) },
            { "Bag of Gems", new HealthDef(0, 10, "PICKUP_ARMOR_10", false, false) },
            { "Diamond", new HealthDef(0, 50, "PICKUP_DIAMOND", false, false) },
        };

        static readonly Dictionary<string, string> PowerupTags = new Dictionary<string, string>
        {
            { "Hallowed Health", "HolyHealthTag" },
            { "Fast Fire Totem", "Weapon Speed Pickup" },
            { "Serum of Blistering Heat", "Superhot Powerup" },
            { "Flashlight", "FlashlightPickupTag" },
            { "Backpack", "BackpackTag" },
        };

        static PlayerPickupScript Picker => Object.FindObjectOfType<PlayerPickupScript>();
        static SelectionScript Selection =>
            GameObject.Find("WeaponAnimator")?.GetComponent<SelectionScript>();

        public static LevelEntry CurrentLevel =>
            LocationTable.LevelByScene.TryGetValue(SceneManager.GetActiveScene().name, out var l) ? l : null;

        public static bool InLevel => CurrentLevel != null && Picker != null && Selection != null;

        /// <summary>Items with an immediate in-game effect wait until the player is in a level.</summary>
        public static bool CanApplyNow(string item)
        {
            if (item.EndsWith(" Access")) return true;
            if (item.EndsWith(" Key")) return true;  // stored; applied when its level loads
            return InLevel;
        }

        /// <summary>Apply one received item. isNew=false means it's a replay on reconnect (state items only).</summary>
        public static void Apply(string item, string sender, bool isNew)
        {
            if (item.EndsWith(" Access"))
            {
                if (isNew) Message($"{item} (from {sender})");
                return;
            }
            if (item.EndsWith(" Key"))
            {
                var lvl = CurrentLevel;
                if (lvl != null && item.StartsWith(lvl.Code + " ") && InLevel)
                {
                    if (isNew) GrantViaPickup(KeyTag(item), null);
                    else SetKey(item, true);
                }
                else if (isNew) Message($"{item} (from {sender})");
                return;
            }
            if (Weapons.TryGetValue(item, out var w))
            {
                if (!InLevel) return; // re-applied on every level load by ApplyPersistentState
                if (isNew)
                    GrantViaPickup(w.Tag, go =>
                    {
                        var s = go.AddComponent<WeaponPickupScript>();
                        s.giveweapon = true; s.weaponcontent = w.Index; s.ammocontent = w.Ammo; s.message = w.Message;
                    });
                ApplyPersistentState();
                return;
            }
            if (item == "Sword")
            {
                if (!InLevel) return;
                if (isNew) GrantViaPickup("SwordTag", null);
                ApplyPersistentState();
                return;
            }
            if (!isNew) return; // everything below is consumable
            if (Ammo.TryGetValue(item, out var a))
            {
                GrantViaPickup("Weapon Pickup", go =>
                {
                    var s = go.AddComponent<WeaponPickupScript>();
                    s.giveweapon = false; s.weaponcontent = a.Index; s.ammocontent = a.Amount; s.message = a.Message;
                });
                return;
            }
            if (Health.TryGetValue(item, out var h))
            {
                GrantViaPickup("Health Pickup", go =>
                {
                    var s = go.AddComponent<HealthPickupScript>();
                    s.myhealthcontent = h.Health; s.myarmorcontent = h.Armor; s.message = h.Message;
                    s.doublehealth = h.DoubleHealth; s.doublearmor = h.DoubleArmor;
                });
                return;
            }
            if (PowerupTags.TryGetValue(item, out var tag))
            {
                GrantViaPickup(tag, go =>
                {
                    if (tag == "BackpackTag")
                    {
                        var b = go.AddComponent<BackpackScript>();
                        b.contents = Selection.maxammo.ToArray(); // a full backpack
                    }
                });
                return;
            }
            Plugin.Log.LogWarning("Unknown item " + item);
        }

        /// <summary>Re-apply everything that should persist: weapons and this level's keys. Called on level load.</summary>
        public static void ApplyPersistentState()
        {
            var sel = Selection;
            var client = Plugin.Client;
            if (sel == null || !client.Connected) return;
            if (client.Categories.Contains("weapons"))
            {
                foreach (var kv in Weapons)
                    if (client.Count(kv.Key) > 0) sel.weaponinventory[kv.Value.Index] = true;
                if (client.Count("Progressive Pistol") >= 2) { sel.havedualpistols = true; sel.permduals = true; }
                if (client.Count("Progressive Shotgun") >= 2) { sel.havedualshotguns = true; sel.permshotguns = true; }
                if (client.Count("Super Shotgun") > 0) { sel.havesupershotgun = true; sel.permsupershotgun = true; }
                if (client.Count("Sword") > 0) { sel.havedaikatana = true; sel.permdaikatana = true; }
            }
            var lvl = CurrentLevel;
            if (lvl != null && client.Categories.Contains("keys"))
                foreach (var color in new[] { "Red Key", "Blue Key", "Yellow Key" })
                    if (client.Count($"{lvl.Code} {color}") > 0) SetKey($"{lvl.Code} {color}", true);
        }

        static string KeyTag(string item) =>
            item.EndsWith("Red Key") ? "RedKeyTag" : item.EndsWith("Blue Key") ? "BlueKeyTag" : "YellowKeyTag";

        static void SetKey(string item, bool value)
        {
            var sel = Selection;
            if (sel == null) return;
            if (item.EndsWith("Red Key")) sel.haveredkey = value;
            else if (item.EndsWith("Blue Key")) sel.havebluekey = value;
            else sel.haveyellowkey = value;
        }

        static void GrantViaPickup(string tag, System.Action<GameObject> configure)
        {
            var picker = Picker;
            if (picker == null) return;
            var go = new GameObject("AP Item");
            go.SetActive(false); // keep the pickup's own Start/Update from running
            go.tag = tag;
            var col = go.AddComponent<BoxCollider>();
            col.isTrigger = true;
            configure?.Invoke(go);
            go.transform.position = picker.transform.position;
            Granting = true;
            try { picker.TryPickupItem(go); }
            finally { Granting = false; }
            if (go != null) Object.Destroy(go);
        }

        /// <summary>Show text where the game shows pickup messages.</summary>
        public static void Message(string text)
        {
            var msg = GameObject.Find("MessageText");
            if (msg == null) { Plugin.Log.LogInfo(text); return; }
            msg.GetComponent<TextMeshProUGUI>().text = text;
            var clear = msg.GetComponent<ClearMessageAfterTime>();
            if (clear != null) clear.timer = clear.defaulttime;
        }
    }
}
