#!/usr/bin/env bash
# Instala o CopyBoard no sistema do usuário: cria venv, instala dependências,
# registra ícone, atalho do menu de aplicativos e (opcionalmente) autostart.
set -e

cd "$(dirname "$0")"
ROOT="$(pwd)"

echo "==> Criando ambiente virtual (.venv)…"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --upgrade pip >/dev/null
./.venv/bin/pip install -r requirements.txt

echo "==> Instalando ícone…"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"
cp -f "$ROOT/resources/icon.png" "$ICON_DIR/copyboard.png"

echo "==> Criando atalho no menu de aplicativos…"
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/copyboard.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CopyBoard
GenericName=Gerenciador de Clipboard
Comment=Histórico do clipboard com atalho global, busca e suporte a imagens
Exec=$ROOT/run.sh
Icon=copyboard
Terminal=false
Categories=Utility;
StartupNotify=false
Keywords=clipboard;copy;paste;history;
EOF
chmod +x "$APPS_DIR/copyboard.desktop" 2>/dev/null || true

# refresh do banco de aplicativos (silencioso se não existir)
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo
echo "✅ Instalado!"
echo "   - Abra pelo menu de aplicativos: 'CopyBoard'"
echo "   - Ou rode diretamente: $ROOT/run.sh"
echo "   - Para iniciar automaticamente no login, abra o app e marque a opção em Configurações."
