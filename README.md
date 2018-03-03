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

## License

GPLv3 until @alejandroautalan decides to [relicense to MIT](alejandroautalan/pygubu/issues/111).
Once that has been done, I'll relicense this project to the ISC license.

    fantaconvert - character conversion utility
    Copyright (C) 2018 oldmud0 <https://github.com/oldmud0>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.