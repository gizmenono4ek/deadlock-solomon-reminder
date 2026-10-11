# Solomon Piece Reminder — GameBanana page text

## Title
Solomon: Don't Forget Your Pieces

## Subtitle
Ability icon blinks red when a piece sits unused for 15s.

## Body
Playing Solomon? Then you know the pain: you drop a Bishop or the Queen, get into a fight, forget to recall it… and the ability never goes on cooldown. Minutes later you realise your 1 or your ult has just been standing in a corner the whole time.

This mod fixes exactly that.

REMINDER
- When a piece is out and you haven't touched it for 15 seconds, its ability icon starts blinking red.
- Pick the piece up, move it, drag it, re-place it — the blinking stops and the timer starts over.
- Heavy melee charge, dash, stuns and other short interruptions don't reset the timer, so no false alarms.
- Only Solomon's icons are affected. Other heroes and items: nothing changes.

Piece colors (gold Queen, silver pieces) moved to the separate Solomon Neon Squares mod, now with a bright neon glow outline on every piece.

Purely visual: a HUD script (one Panorama layout + one tiny CSS + one JS). No gameplay changes, zero FPS impact.

Screenshots are in-game shots.

## Instructions
Easiest way is Deadlock Mod Manager, just install it from here.

Manual install:
1. download and unzip
2. put pak03_dir.vpk into Deadlock/game/citadel/addons
3. if that number is taken, rename to any free one (pak04_dir.vpk, pak05_dir.vpk...)
4. restart the game

If nothing changed in game, open your mod manager once: a Deadlock update sometimes resets gameinfo.gi and mods stop loading.

Won't work together with other mods that replace the ability icon layout (hud_ability_icon). Lower pak number wins.

The delay (15s) and blink speed are configurable if you build from source: github link / see README.

## Changelog
v1.1
- piece colors moved to Solomon Neon Squares (neon glow outline on pieces)

v1.0
- red blink reminder after 15s on an unused piece, resets on any interaction with the piece
- gold Queen, silver Bishop / Rook / Knight
