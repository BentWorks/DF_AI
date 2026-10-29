#!/bin/sh
# Run a DFHack command or Lua in the live game, ANSI codes stripped.
# Usage: df.sh lua "<code>"   |   df.sh <dfhack command...>
DFH="${DFHACK_DIR:-$HOME/snap/steam/common/.local/share/Steam/steamapps/common/DFHack}"
cd "$DFH" && timeout "${DF_TIMEOUT:-60}" ./dfhack-run "$@" 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
