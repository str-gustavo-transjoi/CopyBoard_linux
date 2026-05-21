#!/usr/bin/env bash
# Remove o atalho do menu, ícone e (opcionalmente) o autostart do CopyBoard.
set -e
rm -f "$HOME/.local/share/applications/copyboard.desktop"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/copyboard.png"
rm -f "$HOME/.config/autostart/copyboard.desktop"
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
echo "✅ Atalhos removidos. (A pasta do projeto e o histórico em ~/.local/share/copyboard/ não foram apagados.)"
