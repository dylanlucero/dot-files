#!/usr/bin/env python3
"""Wofi app launcher with DuckDuckGo fallback for unmatched text."""

import configparser
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlencode

CONFIG_DIR = Path(__file__).resolve().parent
ICON_EXTENSIONS = (".png", ".svg", ".xpm", ".jpg", ".jpeg")
CACHE_PATH = CONFIG_DIR / ".launcher-cache.json"
CACHE_TTL_SECONDS = 24 * 60 * 60
ENGINE_PATH = CONFIG_DIR / ".search-engine"
SEARCH_ENGINES = {
    "DuckDuckGo": ("https://duckduckgo.com/", "q"),
    "Google": ("https://www.google.com/search", "q"),
    "Bing": ("https://www.bing.com/search", "q"),
    "Brave Search": ("https://search.brave.com/search", "q"),
    "Startpage": ("https://www.startpage.com/sp/search", "query"),
    "Ecosia": ("https://www.ecosia.org/search", "q"),
    "Qwant": ("https://www.qwant.com/", "q"),
}


def desktop_dirs():
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    return [data_home / "applications", *(Path(p) / "applications" for p in data_dirs.split(":"))]


def desktop_tree_fingerprint():
    """Detect added or removed desktop files by watching application dir mtimes."""
    fingerprint = []
    for root in desktop_dirs():
        if not root.is_dir():
            fingerprint.append([str(root), None])
            continue
        for current, subdirs, _ in os.walk(root):
            subdirs.sort()
            try:
                fingerprint.append([current, Path(current).stat().st_mtime_ns])
            except OSError:
                fingerprint.append([current, None])
    return fingerprint


def icon_index():
    roots = [Path.home() / ".local/share/icons", Path.home() / ".icons", Path("/usr/share/icons"), Path("/usr/share/pixmaps")]
    index = {}
    for root in roots:
        if not root.is_dir():
            continue
        for current, _, files in os.walk(root):
            for filename in files:
                stem = Path(filename).stem
                if Path(filename).suffix.lower() in ICON_EXTENSIONS and stem not in index:
                    index[stem] = str(Path(current) / filename)
    return index


def applications():
    icons = None
    found = {}
    for directory in desktop_dirs():
        if not directory.is_dir():
            continue
        for desktop_file in directory.rglob("*.desktop"):
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.optionxform = str
            try:
                parser.read(desktop_file, encoding="utf-8")
                entry = parser["Desktop Entry"]
            except (OSError, KeyError, configparser.Error):
                continue
            if entry.get("Type", "Application") != "Application":
                continue
            if entry.get("NoDisplay", "false").lower() == "true" or entry.get("Hidden", "false").lower() == "true":
                continue
            name = entry.get("Name", "").strip()
            if not name or name in found:
                continue
            icon = entry.get("Icon", "").strip()
            icon_path = None
            if icon:
                possible = Path(icon).expanduser()
                if possible.is_file():
                    icon_path = str(possible)
                else:
                    if icons is None:
                        icons = icon_index()
                    icon_path = icons.get(Path(icon).stem)
            found[name] = (desktop_file, icon_path)
    return found


def load_applications(refresh=False):
    fingerprint = desktop_tree_fingerprint()
    if not refresh:
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if (
                time.time() - cache["created"] < CACHE_TTL_SECONDS
                and cache.get("desktop_fingerprint") == fingerprint
            ):
                apps = {
                    item["name"]: (Path(item["desktop_file"]), item["icon_path"])
                    for item in cache["apps"]
                    if Path(item["desktop_file"]).is_file()
                }
                if apps:
                    return apps
        except (OSError, ValueError, KeyError, TypeError):
            pass

    apps = applications()
    cache = {
        "created": time.time(),
        "desktop_fingerprint": fingerprint,
        "apps": [
            {"name": name, "desktop_file": str(desktop_file), "icon_path": icon_path}
            for name, (desktop_file, icon_path) in apps.items()
        ],
    }
    temporary = CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    temporary.replace(CACHE_PATH)
    return apps


def selected_engine():
    try:
        name = ENGINE_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        name = "DuckDuckGo"
    return name if name in SEARCH_ENGINES else "DuckDuckGo"


def show_menu(items, prompt, lines=6):
    command = [
        "wofi", "--show", "dmenu", "--allow-images", "--insensitive",
        "--prompt", prompt, "--width", "25%", "--lines", str(lines),
        "--location", "0", "--style", str(CONFIG_DIR / "style.css"),
        "--define=dmenu-parse_action=true",
    ]
    try:
        result = subprocess.run(command, input="\n".join(items) + "\n", text=True, capture_output=True, check=False)
    except OSError:
        return ""
    return result.stdout.strip()


def choose_engine():
    choice = show_menu(list(SEARCH_ENGINES), "Choose search engine", lines=len(SEARCH_ENGINES))
    if choice not in SEARCH_ENGINES:
        return
    temporary = ENGINE_PATH.with_suffix(".tmp")
    temporary.write_text(choice + "\n", encoding="utf-8")
    temporary.replace(ENGINE_PATH)


def main():
    refresh_cache = "--refresh-cache" in sys.argv
    apps = load_applications(refresh=refresh_cache)
    if refresh_cache:
        return 0
    if not apps:
        return 1

    rows = []
    engine_label = f"⚙ Search engine ({selected_engine()})"
    for name, (_, icon_path) in sorted(apps.items(), key=lambda item: item[0].casefold()):
        if icon_path:
            rows.append(f"img:{icon_path}:text:{name}")
        else:
            rows.append(name)
    rows.append(engine_label)

    choice = show_menu(rows, "Apps or search the web")
    if not choice:
        return 0
    if choice == engine_label:
        choose_engine()
        return 0

    app = apps.get(choice)
    if app:
        subprocess.Popen(["gio", "launch", str(app[0])], start_new_session=True)
    else:
        base_url, parameter = SEARCH_ENGINES[selected_engine()]
        query_url = base_url + "?" + urlencode({parameter: choice})
        subprocess.Popen(["xdg-open", query_url], start_new_session=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
