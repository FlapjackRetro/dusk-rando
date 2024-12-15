This is a randomizer of the video game Dusk (https://store.steampowered.com/app/519860/DUSK/) by David Szymanski.

The goal is to implement a randomizer and pair it with Archipelago (https://archipelago.gg).

This is currently a very slow work-in-progress as I have never built a randomizer before, and it's been more than a decade since I've used C#, and never since using Python.

Initially this will just be item randomization, although I intend to also change the way access to weapons and keys are implemented, to bring the behavior inline with other boomer shooters on Archieplago (DOOM and Duke Nukem).

TODO:
 - Document all items in Dusk that need to be randomized
 - Create function to randomize items using logic to prevent softlocks
 - Create function to intercept the game's vanilla item-handler and instead distribute items from a randomizer output file
 - Create function to unlock levels in an arbitrary order
 - BONUS: create function to update models of randomized items on scene load (level load)
 
