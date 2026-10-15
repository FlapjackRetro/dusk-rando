using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using Archipelago.MultiClient.Net.Enums;
using DuskRando.Patches;
using UnityEngine;
using Object = UnityEngine.Object;

namespace DuskRando
{
    /// <summary>
    /// Makes randomized pickups look like what they actually contain (issue #4).
    ///
    /// DUSK items wear the matching DUSK model. The game has no asset we can load by name, so models are
    /// harvested from what is loaded: every pickup placed in a scene we visit, plus the prefabs listed in
    /// SaveManagerScript.spawnableitems (ammo, health, morale, keys, backpack, which every level carries).
    /// Copies are stripped down to their renderers and kept in a hidden DontDestroyOnLoad library, so the
    /// library grows as you play. A DUSK item whose model hasn't been seen yet falls back to an AP logo.
    ///
    /// Items for other games (or DUSK items for another player) use one of three AP logo sprites:
    /// grey = filler/trap, colour = useful, colour + arrow = progression.
    /// </summary>
    public static class ItemModels
    {
        static GameObject library;
        static readonly Dictionary<string, GameObject> templates = new Dictionary<string, GameObject>();
        static Sprite filler, useful, progression;

        // Item name -> scene object name of a pickup that looks like it (see docs/LOCATIONS.csv "object").
        static readonly Dictionary<string, string> ItemObject = new Dictionary<string, string>
        {
            { "Progressive Pistol", "PistolPickup" }, { "Progressive Shotgun", "ShotgunPickup" },
            { "Super Shotgun", "SuperShotgunPickup" }, { "Assault Rifle", "MachineGunPickup" },
            { "Hunting Rifle", "RiflePickup" }, { "Crossbow", "ChainsawPickup" }, { "Mortar", "BuzzSawPickup" },
            { "Riveter", "RiveterPickup" }, { "Sword", "SwordPickup" },
            { "Hallowed Health", "holyhealth" }, { "Fast Fire Totem", "weaponspeedpickup" },
            { "Serum of Blistering Heat", "superhotpickup" }, { "Flashlight", "flashlightpickup" },
            { "Backpack", "backpack" },
            { "Medical Kit", "healthpack" }, { "Small Medical Kit", "minihealthpack" }, { "Magic Potion", "healthbonus" },
            { "Gold Coin", "armorbonus" }, { "Bag of Gems", "tenarmor" }, { "Diamond", "ArmorDiamond" },
            { "Pistol Bullet", "pistolbullet" }, { "Pistol Clip", "pistolclip" }, { "Box of Pistol Bullets", "bulletbox" },
            { "Shotgun Shell", "singleshotgunshellpickup" }, { "Box of Shotgun Shells", "shotgunshells" },
            { "Assault Rifle Magazine", "m16clip" }, { "Hunting Rifle Bullet", "riflebullet" },
            { "Box of Hunting Rifle Bullets", "RifleBoxPickup" }, { "Crossbow Bolts", "CrossbowAmmoPickup" },
            { "Mortar Grenade", "mortarammo" }, { "Box of Mortar Grenades", "grenadebox" }, { "Rivets", "riveterammo" },
        };

        // Keys look different per episode: E1 keys, E2 keycards, E3 magic keys.
        static readonly string[] KeyStyle = { null, "{0}Key", "{0}Card", "{0}KeyMagic" };

        static readonly Regex CopySuffix = new Regex(@"( \(\d+\))+$|\(Clone\)$");

        public static void Init()
        {
            library = new GameObject("DuskRando Model Library");
            library.SetActive(false); // nothing inside ever runs Awake/Start or renders
            Object.DontDestroyOnLoad(library);
            filler = LoadSprite("ap_filler.png");
            useful = LoadSprite("ap_useful.png");
            progression = LoadSprite("ap_progression.png");
        }

        static Sprite LoadSprite(string file)
        {
            byte[] bytes;
            using (var s = typeof(ItemModels).Assembly.GetManifestResourceStream("DuskRando.Assets." + file))
            using (var ms = new MemoryStream())
            {
                s.CopyTo(ms);
                bytes = ms.ToArray();
            }
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point };
            tex.LoadImage(bytes);
            // 160 px per unit: the 128 px logo is ~0.8 units across, about the size of a DUSK pickup.
            return Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 160f);
        }

        static string BaseName(string name) => CopySuffix.Replace(name, "");

        /// <summary>Copy the look of everything pickup-like in the freshly loaded scene into the library.</summary>
        public static void Harvest()
        {
            foreach (var p in Object.FindObjectsOfType<SavePickupScript>())
                if (!p.CompareTag("SecretTag")) AddTemplate(p.gameObject);
            var save = Object.FindObjectOfType<SaveManagerScript>();
            if (save != null && save.spawnableitems != null)
                foreach (var prefab in save.spawnableitems)
                    if (prefab != null) AddTemplate(prefab);
        }

        static void AddTemplate(GameObject source)
        {
            var name = BaseName(source.name);
            if (templates.ContainsKey(name)) return;
            if (source.GetComponentInChildren<Renderer>(true) == null) return;
            var copy = Object.Instantiate(source, library.transform, false);
            copy.name = name;
            StripToVisuals(copy);
            copy.transform.localPosition = Vector3.zero;
            copy.transform.localRotation = Quaternion.identity;
            copy.transform.localScale = source.transform.lossyScale; // remembered so copies come out the same size
            templates[name] = copy;
        }

        /// <summary>Remove everything but transforms and renderers. Some components depend on others, so loop.</summary>
        static void StripToVisuals(GameObject go)
        {
            for (int pass = 0; pass < 4; pass++)
            {
                bool removedAny = false;
                foreach (var c in go.GetComponentsInChildren<Component>(true))
                {
                    if (c == null || c is Transform || c is MeshFilter || c is MeshRenderer ||
                        c is SkinnedMeshRenderer || c is SpriteRenderer)
                        continue;
                    // Behaviours first; physics/audio/etc. on later passes once nothing requires them.
                    if (pass == 0 && !(c is Behaviour)) continue;
                    Object.DestroyImmediate(c);
                    removedAny = true;
                }
                if (!removedAny && pass > 0) break;
            }
        }

        /// <summary>Dress a randomized pickup as the item it holds. Safe to call more than once.</summary>
        public static void Apply(ApLocation loc)
        {
            if (loc == null || loc.Sent || loc.Dressed) return;
            if (loc.CompareTag("SecretTag") || loc.GetComponent<TreasureChestScript>() != null) return; // nothing to show
            var scout = Plugin.Client.GetScout(loc.Id);
            if (scout == null) return; // not scouted yet; Plugin retries when scouting finishes

            GameObject template = null;
            if (scout.ForDusk && TemplateNameFor(scout.ItemName, out var objName))
                templates.TryGetValue(objName, out template);
            if (template != null && template.name == BaseName(loc.gameObject.name))
            {
                loc.Dressed = true; // already looks right
                return;
            }

            foreach (var r in loc.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            GameObject visual;
            if (template != null)
            {
                visual = Object.Instantiate(template, loc.transform, false);
                var parentScale = loc.transform.lossyScale;
                var wanted = template.transform.localScale;
                visual.transform.localScale = new Vector3(
                    SafeDiv(wanted.x, parentScale.x), SafeDiv(wanted.y, parentScale.y), SafeDiv(wanted.z, parentScale.z));
            }
            else
            {
                visual = new GameObject("AP Item");
                visual.transform.SetParent(loc.transform, false);
                var sr = visual.AddComponent<SpriteRenderer>();
                sr.sprite = SpriteFor(scout.Flags);
                var parentScale = loc.transform.lossyScale;
                visual.transform.localScale = new Vector3(SafeDiv(1, parentScale.x), SafeDiv(1, parentScale.y), SafeDiv(1, parentScale.z));
                visual.transform.localPosition = new Vector3(0, SafeDiv(0.3f, parentScale.y), 0);
            }
            visual.name = "AP Visual";
            visual.transform.localRotation = Quaternion.identity;
            if (template != null) visual.transform.localPosition = Vector3.zero;
            visual.SetActive(true);
            loc.Dressed = true;
        }

        static float SafeDiv(float a, float b) => Mathf.Abs(b) < 1e-5f ? a : a / b;

        static Sprite SpriteFor(ItemFlags flags)
        {
            if ((flags & ItemFlags.Advancement) != 0) return progression;
            if ((flags & ItemFlags.NeverExclude) != 0) return useful;
            return filler; // filler and traps
        }

        static bool TemplateNameFor(string item, out string objName)
        {
            if (ItemObject.TryGetValue(item, out objName)) return true;
            // "E2M3 Red Key" -> "RedCard"
            if (item.EndsWith(" Key") && item.Length > 6 && item[0] == 'E' && char.IsDigit(item[1]))
            {
                int episode = item[1] - '0';
                var color = item.Substring(item.IndexOf(' ') + 1).Replace(" Key", "");
                if (episode >= 1 && episode <= 3)
                {
                    objName = string.Format(KeyStyle[episode], color);
                    return true;
                }
            }
            objName = null;
            return false;
        }
    }
}
