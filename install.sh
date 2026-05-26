#!/usr/bin/env bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==>${NC} Запуск установки сборки cachyos-apex..."

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$REPO_DIR/configs"
LOCAL_DIR="$REPO_DIR/local-data"
BACKUP_DIR="$HOME/.config/kde-backup-$(date +%Y%m%d_%H%M%S)"

# Проверить наличие paru
if ! command -v paru &> /dev/null; then
    echo -e "${RED}Ошибка:${NC} paru (AUR helper) не найден. Пожалуйста, установите paru перед продолжением."
    exit 1
fi

# 1. Установка пакетов
if [ -f "$REPO_DIR/pkglist.txt" ]; then
    echo -e "${BLUE}==>${NC} Установка системных пакетов из pkglist.txt..."
    packages=$(grep -v '^#' "$REPO_DIR/pkglist.txt" | xargs)
    if [ -n "$packages" ]; then
        paru -S --needed --noconfirm $packages
    fi
fi

if [ -f "$REPO_DIR/aur-pkglist.txt" ]; then
    echo -e "${BLUE}==>${NC} Установка AUR пакетов из aur-pkglist.txt..."
    aur_packages=$(grep -v '^#' "$REPO_DIR/aur-pkglist.txt" | xargs)
    if [ -n "$aur_packages" ]; then
        paru -S --needed --noconfirm $aur_packages
    fi
fi

# 2. Создание бэкапа
echo -e "${BLUE}==>${NC} Создание резервной копии текущих настроек в $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"

FILES_TO_BACKUP=(
    ".config/kdeglobals"
    ".config/plasma-org.kde.plasma.desktop-appletsrc"
    ".config/plasmashellrc"
    ".config/plasmarc"
    ".config/kwinrc"
    ".config/kglobalshortcutsrc"
    ".config/kcminputrc"
    ".config/krunnerrc"
    ".config/kscreenlockerrc"
    ".config/kwinrulesrc"
)

for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$HOME/$file" ]; then
        mkdir -p "$(dirname "$BACKUP_DIR/${file#.config/}")"
        cp "$HOME/$file" "$BACKUP_DIR/${file#.config/}"
    fi
done
echo -e "   ${GREEN}✓${NC} Бэкап завершен"

# 3. Применение конфигурационных файлов
echo -e "${BLUE}==>${NC} Применение настроек KDE..."
if [ -d "$CONFIG_DIR" ]; then
    cp -r "$CONFIG_DIR"/* "$HOME/.config/"
    echo -e "   ${GREEN}✓${NC} Настройки скопированы в ~/.config/"
fi

# 4. Применение локальных ресурсов (темы, виджеты)
echo -e "${BLUE}==>${NC} Установка тем, иконок и виджетов..."
if [ -d "$LOCAL_DIR" ]; then
    mkdir -p "$HOME/.local/share"
    cp -r "$LOCAL_DIR"/* "$HOME/.local/share/"
    echo -e "   ${GREEN}✓${NC} Ресурсы скопированы в ~/.local/share/"
fi

# 5. Перезапуск Plasma Shell
echo -e "${BLUE}==>${NC} Перезапуск KDE Plasma для применения изменений..."
systemctl --user restart plasma-plasmashell.service
qdbus6 org.kde.KWin /KWin reconfigure 2>/dev/null || qdbus org.kde.KWin /KWin reconfigure 2>/dev/null

echo -e "${GREEN}==>${NC} Установка cachyos-apex успешно завершена!"
