# CopyBoard

Gerenciador de histórico do clipboard para **Linux** com atalho global, busca instantânea, suporte a imagens e bandeja do sistema.

<p align="center">
  <img src="resources/icon.png" alt="CopyBoard" width="128" height="128">
</p>

> Porte do app original CopyBoard (macOS, Swift/SwiftUI). Mesmo fluxo, mesma interface, mesma logo.

## Recursos

- 📋 Captura automática de tudo que é copiado (texto e imagens)
- 🔍 Busca em tempo real (com debounce) e filtro `*image`
- ⌨️ Atalho global configurável (padrão: **Ctrl + Shift + V**)
- 🖼️ Cache de thumbnails e paginação ("Carregar mais")
- ✅ Modo seleção: copiar/excluir vários itens
- ⚡ Ao escolher um item: copia para o clipboard e cola automaticamente
- 🧹 Limpar histórico por período (manter X dias / apagar X dias)
- 🌗 Tema claro/escuro/sistema
- 🚀 Inicialização automática no login
- 🗂️ Persistência em SQLite (`~/.local/share/copyboard/history.db`)

## Requisitos

- Linux com Python **3.10+**
- `python3-venv` (ou equivalente da sua distro)
- Sessão **X11/Xorg** recomendada (no Wayland o atalho global e a colagem automática podem ser bloqueados pelo compositor)

### Instalando dependências do sistema (se faltar)

```bash
# Ubuntu / Debian / Mint / Pop!_OS:
sudo apt update && sudo apt install -y \
    python3 python3-venv python3-pip \
    libxcb-cursor0 libxkbcommon-x11-0 libgl1

# Fedora:
sudo dnf install -y python3 python3-pip libxcb xcb-util-cursor mesa-libGL

# Arch / Manjaro:
sudo pacman -S --needed python python-pip xcb-util-cursor
```

## Instalação rápida (clone + executar)

```bash
git clone https://github.com/SEU_USUARIO/CopyBoard.git
cd CopyBoard
./run.sh
```

> ✨ Na primeira execução o script cria um `.venv`, instala as dependências
> (`PySide6`, `pynput`) e abre o app. Nas próximas vezes ele só inicia.

## Instalação completa (atalho no menu + ícone)

Para registrar o **CopyBoard no menu de aplicativos** do seu desktop, com ícone:

```bash
./install.sh
```

O script:

- cria o `.venv` e instala as dependências
- copia o ícone para `~/.local/share/icons/hicolor/256x256/apps/copyboard.png`
- cria o atalho `~/.local/share/applications/copyboard.desktop`
- atualiza os caches de aplicativos/ícones do desktop

Depois você abre o app pelo menu (procure por **CopyBoard**) ou pelo terminal com `./run.sh`.

Para remover os atalhos:

```bash
./uninstall.sh
```

## Uso

1. Inicie o app — ele aparece como ícone na **bandeja do sistema**.
2. Copie qualquer texto ou imagem normalmente (`Ctrl+C`).
3. Pressione **Ctrl + Shift + V** (ou clique no ícone da bandeja) para abrir o histórico.
4. Clique em um item: ele é copiado para o clipboard e colado automaticamente na janela ativa.
5. Use o campo de busca para filtrar. Digite `*image` para listar somente imagens.
6. Botão **Selecionar** habilita seleção múltipla para copiar/excluir em lote.

### Menu da bandeja

- **Abrir Histórico** — abre a janela do histórico
- **Alterar Atalho** — captura um novo atalho global
- **Configurações** — tema, limpar histórico, autostart, imagens on/off
- **Sair** — encerra o app

## ⚠️ X11 vs Wayland

| Recurso                        | X11 / Xorg | Wayland |
|--------------------------------|:----------:|:-------:|
| Histórico do clipboard         | ✅          | ✅       |
| Bandeja do sistema             | ✅          | ✅¹      |
| Atalho global (hotkey)         | ✅          | ⚠️²     |
| Simulação automática de paste  | ✅          | ⚠️²     |

¹ Depende do compositor (no GNOME pode exigir a extensão *AppIndicator and KStatusNotifierItem Support*).
² Bloqueado por segurança pelo Wayland. Alternativa: registrar um **atalho personalizado** nas Configurações de Teclado do seu desktop apontando para o comando `copyboard` — o app já estará rodando em segundo plano via bandeja.

Para experiência completa, use uma sessão **X11/Xorg** (no GDM/SDDM, selecione "GNOME on Xorg" ao fazer login).

## Permissões (atalho global)

Em algumas distros o `pynput` precisa que o usuário esteja no grupo `input`:

```bash
sudo usermod -aG input $USER
# faça logout/login depois
```

## Estrutura do projeto

```
.
├── copyboard/              # pacote Python principal
│   ├── app.py              # entry point + wiring
│   ├── db.py               # SQLite (WAL)
│   ├── monitor.py          # ClipboardMonitor (dedupe + prune)
│   ├── hotkey.py           # atalho global via pynput
│   ├── hotkey_capture.py   # diálogo de captura de atalho
│   ├── history_window.py   # popup do histórico
│   ├── settings_window.py  # janela de configurações
│   ├── tray.py             # ícone na bandeja
│   ├── settings.py         # QSettings wrapper
│   └── constants.py
├── resources/
│   ├── icon.png            # logo do app (mesma da versão macOS)
│   ├── icon-64.png
│   └── icon-512.png
├── requirements.txt
├── pyproject.toml          # `pip install .` → comando `copyboard`
├── run.sh                  # cria venv e inicia o app
├── install.sh              # instala atalho + ícone no sistema
├── uninstall.sh            # remove atalhos do sistema
├── copyboard.desktop       # template de entry de aplicativo
└── README.md
```

## Empacotar / Distribuir

### Instalação como comando do sistema

```bash
pip install .
copyboard
```

### Binário standalone (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --name copyboard --windowed --onefile -m copyboard
# binário em dist/copyboard
```

### AppImage (portável)

Veja [appimagetool](https://github.com/AppImage/AppImageKit) para empacotar o binário do PyInstaller em um `.AppImage` único.

## Arquivos e dados do usuário

| Caminho                                                   | Conteúdo                       |
|-----------------------------------------------------------|--------------------------------|
| `~/.local/share/copyboard/history.db`                     | Banco SQLite do histórico      |
| `~/.config/CopyBoard/CopyBoard.conf`                      | Preferências (QSettings)       |
| `~/.config/autostart/copyboard.desktop`                   | Autostart (opcional)           |
| `~/.local/share/applications/copyboard.desktop`           | Atalho do menu (após install)  |
| `~/.local/share/icons/hicolor/256x256/apps/copyboard.png` | Ícone (após install)           |

## Contribuindo

Pull requests são bem-vindos! Para mudanças grandes, abra uma issue antes para discutirmos.

## Licença

MIT — sinta-se livre para usar, modificar e distribuir.
