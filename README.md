# Winterdeep Campaign

A players' journal for our Thursday-night D&D 5e campaign, Winterdeep: where the party is, quests, sessions, NPCs, places, factions, items, lore and a timeline.

Live: https://wernercd.github.io/dnd-winterdeep/ (static site in `site/`, deployed by GitHub Pages on every push to `main`).

## Updating
`site/data.js` is generated from the private campaign notes kept outside this repo:

```
python tools/build_data.py --kb <path to the private notes>
```

The build publishes campaign content only. It replaces players with their characters and leaves out session recordings, transcripts, quotes and chat. If any blocked word gets through, it stops with an error. Add a change-log entry in `site/changes.html` for each update.

Part of the D&D Toolbox and follows its shared conventions (`WernerCD/dnd`, `STYLE.md`).

Unofficial fan content, not affiliated with or endorsed by Wizards of the Coast.
