# fantaconvert - character conversion utility

This script attempts to convert char.ini-based characters from FanatSors'
Attorney Online family of games to the Animated Chatroom/Attorney Online 3 JSON
format.

You may need Python 3, but if I have time, I'll run it through cx_Freeze to
make a standalone executable.

## Notes

- Only one set of button icons is used, since a selection effect is applied to
  the icon procedurally.
- Large GIFs ought to be converted to WebM first. This yields significant
  space savings.
- Sound effects are extracted from the installation and placed on the asset.

## Disclaimer

THIS PROCESS IS IRREVERSIBLE.

## To-do

- Support parent system for deduplication.
- Add other authoring tools.