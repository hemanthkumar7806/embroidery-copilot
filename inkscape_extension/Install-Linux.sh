#!/bin/sh
# StitchBase - extension one-click installer (Linux)
# Copies the extension, verifies it, checks if Inkscape is running, pings the
# live service (informational), and shows a native popup with the result.

SRC="$(cd "$(dirname "$0")" && pwd)"
HEALTH_URL="https://stitchbase.duckdns.org/health"
DEST="$HOME/.config/inkscape/extensions"

popup() {
  # $1 = message, $2 = "ok" or "err"
  if command -v zenity >/dev/null 2>&1; then
    if [ "$2" = "err" ]; then
      zenity --error --title="StitchBase" --text="$1" >/dev/null 2>&1
    else
      zenity --info --title="StitchBase" --text="$1" >/dev/null 2>&1
    fi
  elif command -v kdialog >/dev/null 2>&1; then
    if [ "$2" = "err" ]; then
      kdialog --title "StitchBase" --error "$1" >/dev/null 2>&1
    else
      kdialog --title "StitchBase" --msgbox "$1" >/dev/null 2>&1
    fi
  else
    printf '\n%s\n\n' "$1"
  fi
}

echo "Installing StitchBase extension..."

ok=1
mkdir -p "$DEST" 2>/dev/null || ok=0
cp -f "$SRC/send_to_ai.py"  "$DEST/" 2>/dev/null || ok=0
cp -f "$SRC/send_to_ai.inx" "$DEST/" 2>/dev/null || ok=0
[ -f "$DEST/send_to_ai.py" ] && [ -f "$DEST/send_to_ai.inx" ] || ok=0

if [ "$ok" != "1" ]; then
  msg="Installation FAILED.

Could not copy the files to:
$DEST

Please copy send_to_ai.py and send_to_ai.inx into your Inkscape user
extensions folder manually (see INSTALL.txt), then restart Inkscape."
  echo "$msg"
  popup "$msg" err
  exit 1
fi

# Is Inkscape running? (needs a full restart to load the extension)
restart_line="Next: open Inkscape."
if pgrep -i inkscape >/dev/null 2>&1; then
  restart_line="IMPORTANT: Inkscape is open - FULLY close and reopen it so the extension loads."
fi

# Informational service reachability check (never fails the install)
if curl -fsS --max-time 6 "$HEALTH_URL" >/dev/null 2>&1; then
  service_line="Service check: online and reachable."
else
  service_line="Service check: could not reach the server right now (does not affect the install)."
fi

msg="Installation successful!

Installed to:
$DEST

$restart_line

Then use:
   Extensions > StitchBase > Open in StitchBase

$service_line"
echo "$msg"
popup "$msg" ok
exit 0
