#!/usr/bin/env bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==>${NC} Запуск экспорта конфигурации cachyos-apex..."

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$REPO_DIR/configs"
LOCAL_DIR="$REPO_DIR/local-data"

mkdir -p "$CONFIG_DIR"
mkdir -p "$LOCAL_DIR"

# 1. Экспорт списка установленных пакетов
echo -e "${BLUE}==>${NC} Сохранение списка установленных пакетов..."
# Явно установленные из официальных репозиториев (не зависимости)
pacman -Qent | awk '{print $1}' > "$REPO_DIR/pkglist.txt"
# Явно установленные из AUR (foreign)
pacman -Qemt | awk '{print $1}' > "$REPO_DIR/aur-pkglist.txt"
echo -e "   ${GREEN}✓${NC} Списки пакетов сохранены (pkglist.txt, aur-pkglist.txt)"

# 2. Копирование основных файлов настроек KDE Plasma 6
echo -e "${BLUE}==>${NC} Копирование конфигурационных файлов KDE..."
FILES_TO_COPY=(
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

for file in "${FILES_TO_COPY[@]}"; do
    if [ -f "$HOME/$file" ]; then
        # Создаем поддиректорию в configs если нужно
        mkdir -p "$(dirname "$CONFIG_DIR/${file#.config/}")"
        cp "$HOME/$file" "$CONFIG_DIR/${file#.config/}"
        echo -e "   ${GREEN}✓${NC} Скопирован $file"
    else
        echo -e "   ${YELLOW}⚠${NC} Файл $file не найден, пропуск"
    fi
done

# 3. Копирование кастомных ресурсов (темы, виджеты, иконки)
echo -e "${BLUE}==>${NC} Копирование локальных ресурсов (виджеты, темы, цветовые схемы)..."

copy_local_dir() {
    local src_dir="$HOME/.local/share/$1"
    local dest_dir="$LOCAL_DIR/$1"
    if [ -d "$src_dir" ] && [ "$(ls -A "$src_dir")" ]; then
        mkdir -p "$dest_dir"
        cp -r "$src_dir"/* "$dest_dir/"
        echo -e "   ${GREEN}✓${NC} Скопирована папка ~/.local/share/$1"
    else
        echo -e "   ${YELLOW}⚠${NC} Папка ~/.local/share/$1 пуста или не существует"
    fi
}

copy_local_dir "plasma/plasmoids"
copy_local_dir "plasma/look-and-feel"
copy_local_dir "color-schemes"
copy_local_dir "icons"
copy_local_dir "themes"
copy_local_dir "wallpapers"

# 4. Проверим текущие обои и попробуем скопировать их
echo -e "${BLUE}==>${NC} Поиск текущих обоев..."
# Извлекаем путь к обоям из plasma-org.kde.plasma.desktop-appletsrc
if [ -f "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc" ]; then
    WALLPAPER_PATH=$(grep -oP "(?<=Image=file://).*$" "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc" | head -n 1)
    if [ -n "$WALLPAPER_PATH" ] && [ -f "$WALLPAPER_PATH" ]; then
        mkdir -p "$LOCAL_DIR/wallpapers"
        cp "$WALLPAPER_PATH" "$LOCAL_DIR/wallpapers/"
        echo -e "   ${GREEN}✓${NC} Скопированы обои: $(basename "$WALLPAPER_PATH")"
    else
        echo -e "   ${YELLOW}⚠${NC} Не удалось автоматически скопировать файл обоев (возможно, используются стандартные или слайд-шоу)"
    fi
fi

echo -e "${GREEN}==>${NC} Экспорт успешно завершен! Проверьте папку репозитория."
