# DUSK Randomizer Setup Guide

## Required software

- DUSK (Steam version)
- [BepInEx 5 (x64)](https://github.com/BepInEx/BepInEx/releases)
- The DUSK Archipelago mod (`DuskRando.dll` plus `Archipelago.MultiClient.Net.dll` and `Newtonsoft.Json.dll`)
- The `dusk.apworld` file, installed into your Archipelago installation's `custom_worlds` folder

## Installation

1. Extract BepInEx into the DUSK folder (the one containing `Dusk.exe`) and start the game once so BepInEx creates
   its folders, then quit.
2. Copy the mod's DLLs into `Dusk/BepInEx/plugins/DuskRando/`.
3. Start DUSK. Press **F1** to open the Archipelago connection window, enter the server, slot name and password, then
   connect before starting a new game.

## Generating a game

Create a player YAML (generate a template from the Archipelago Launcher, "Generate Template Options") with
`game: DUSK` and generate as usual.
