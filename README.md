# fantaconvert - character conversion utility

This script attempts to convert char.ini-based characters from FanatSors'
Attorney Online family of games to the Animated Chatroom/Attorney Online 3 JSON
format.

You may need Python 3, but if I have time, I'll run it through cx_Freeze to
make a standalone executable.

## Notes

- Only one set of button icons is used, since a selection effect is applied to
  the icon procedurally.
- Explicit lengths and delays in emotes are lost because the format does not
  support it.
- Some AO1 assets use Windows-1252 or Windows-1251 (Cyrillic), so the encoding
  must be inferred first and then converted to UTF-8.
- Large GIFs ought to be converted to WebM first. This yields significant
  space savings.
- Sound effects are extracted from the installation and placed on the asset.

## Disclaimer

THIS PROCESS IS IRREVERSIBLE.

## To-do

- Support parent system for deduplication.
- Add other authoring tools.