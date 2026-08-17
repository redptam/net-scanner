#!/usr/bin/env bash
# Download Inter TTF font files for Network Scanner Pro.
# Source: https://github.com/rsms/inter (Apache 2.0 license)
# Place TTF files in net_scanner_gui/fonts/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONT_DIR="$(cd "$SCRIPT_DIR/../fonts" && pwd)"

mkdir -p "$FONT_DIR"

echo "Downloading Inter font files to $FONT_DIR ..."

for weight in Regular Medium SemiBold; do
    url="https://github.com/rsms/inter/releases/download/v4.0/ttf-${weight}.zip"
    echo "  [$weight] $url"
done

echo ""
echo "Each TTF file is in its own zip. Downloading..."

for weight in Regular Medium SemiBold; do
    zip_file="$FONT_DIR/ttf-${weight}.zip"
    if curl -sL "https://github.com/rsms/inter/releases/download/v4.0/ttf-${weight}.zip" -o "$zip_file"; then
        unzip -o -j "$zip_file" "Inter-${weight}.ttf" -d "$FONT_DIR"
        rm -f "$zip_file"
        echo "  ✓ Inter-${weight}.ttf"
    else
        echo "  ✗ Failed to download Inter-${weight}.ttf"
        echo "    Manual: https://github.com/rsms/inter/releases/tag/v4.0"
    fi
done

echo ""
echo "Done. Verify fonts/Inter-Regular.ttf, fonts/Inter-Medium.ttf, fonts/Inter-SemiBold.ttf exist."
