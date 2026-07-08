#!/usr/bin/env python3
"""Build AppImage for VeneraNext Flutter application."""

import argparse
import os
import re
import shutil
import stat
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBSPEC_PATH = ROOT / "pubspec.yaml"
BUILD_LINUX_DIR = ROOT / "build" / "linux"
BUNDLE_DIR = BUILD_LINUX_DIR / "x64" / "release" / "bundle"
APPIMAGE_DIR = BUILD_LINUX_DIR / "appimage"

APPIMAGE_TOOL_VERSION = "continuous"
LINUXDEPLOY_PLUGIN_GTK_VERSION = "continuous"

APPIMAGE_TOOL_URL = (
    "https://github.com/AppImage/AppImageKit/releases/download"
    f"/{APPIMAGE_TOOL_VERSION}/appimagetool-x86_64.AppImage"
)
LINUXDEPLOY_URL = (
    "https://github.com/linuxdeploy/linuxdeploy/releases/download"
    f"/{LINUXDEPLOY_PLUGIN_GTK_VERSION}/linuxdeploy-x86_64.AppImage"
)
LINUXDEPLOY_PLUGIN_GTK_URL = (
    "https://github.com/linuxdeploy/linuxdeploy-plugin-gtk/releases/download"
    f"/{LINUXDEPLOY_PLUGIN_GTK_VERSION}/linuxdeploy-plugin-gtk-x86_64.AppImage"
)


class AppImageBuildError(RuntimeError):
    pass


def _clean_value(value: str) -> str:
    value = value.strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _top_level_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(?P<value>.+?)\s*$", text, re.MULTILINE)
    if not match:
        raise AppImageBuildError(f"pubspec.yaml does not contain {key}")
    return _clean_value(match.group("value"))


def _download_file(url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IEXEC)


def _run(command: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def _create_desktop_file() -> str:
    return """[Desktop Entry]
Name=VeneraNext
GenericName=VeneraNext
Comment=A comic app.
Terminal=false
Type=Application
Categories=Utility;
Exec=venera-next
Icon=venera-next
Keywords=Flutter;comic;images;
"""


def _create_appimage_recipe() -> str:
    return """[AppDirBuilder]
Builder = AppImageBuilder

[AppImageBuilder]
# Integration information
update-information = None
sign-key = None

# AppDir paths configuration
file_name = VeneraNext-{version}-x86_64.AppImage
AppDir = appimage/AppDir

# AppDir content
AppImage:
  arch: x86_64
  update-information: None
  sign-key: None
  file_name: VeneraNext-{version}-x86_64.AppImage

AppDir:
  path: appimage/AppDir
  app_info:
    id: com.github.cyrilpeng.veneranext
    name: VeneraNext
    icon: venera-next
    version: {version}
    exec: usr/bin/venera-next
    exec_args: $@
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build AppImage for VeneraNext")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Prepare AppDir without building AppImage",
    )
    args = parser.parse_args()

    # Read version from pubspec.yaml
    text = PUBSPEC_PATH.read_text(encoding="utf-8")
    version = _top_level_value(text, "version")

    print(f"Building AppImage for VeneraNext v{version}")

    # Check if Flutter build exists
    if not BUNDLE_DIR.exists():
        raise AppImageBuildError(
            f"Flutter bundle directory not found: {BUNDLE_DIR}\n"
            "Please run 'flutter build linux' first."
        )

    # Prepare AppDir structure
    if APPIMAGE_DIR.exists():
        shutil.rmtree(APPIMAGE_DIR)

    appdir = APPIMAGE_DIR / "AppDir"
    appdir.mkdir(parents=True)

    # Create directory structure
    usr_dir = appdir / "usr"
    usr_bin_dir = usr_dir / "bin"
    usr_lib_dir = usr_dir / "lib"
    usr_share_dir = usr_dir / "share"
    applications_dir = usr_share_dir / "applications"
    icons_dir = usr_share_dir / "icons" / "hicolor" / "256x256" / "apps"

    for d in [usr_bin_dir, usr_lib_dir, applications_dir, icons_dir]:
        d.mkdir(parents=True)

    # Copy bundle contents
    print(f"Copying bundle from {BUNDLE_DIR}")
    shutil.copytree(BUNDLE_DIR, usr_bin_dir, dirs_exist_ok=True)

    # Rename executable if needed
    executable = usr_bin_dir / "venera-next"
    if not executable.exists():
        # Try to find any executable in the bundle
        for f in usr_bin_dir.iterdir():
            if f.is_file() and os.access(f, os.X_OK):
                f.rename(usr_bin_dir / "venera-next")
                break

    # Copy desktop file
    desktop_file = appdir / "venera-next.desktop"
    desktop_file.write_text(_create_desktop_file(), encoding="utf-8")

    # Copy icon
    icon_src = ROOT / "debian" / "gui" / "venera-next.png"
    if icon_src.exists():
        shutil.copy2(icon_src, icons_dir / "venera-next.png")
    else:
        # Try alternative icon locations
        alt_icons = [
            ROOT / "assets" / "app_icon.png",
            ROOT / "assets" / "Venera-Next.svg",
        ]
        for alt_icon in alt_icons:
            if alt_icon.exists():
                shutil.copy2(alt_icon, icons_dir / "venera-next.png")
                break

    # Create symlink for AppRun
    apprun = appdir / "AppRun"
    if apprun.exists():
        apprun.unlink()
    apprun.symlink_to("usr/bin/venera-next")

    if args.prepare_only:
        print(f"Prepared AppDir at {appdir}")
        return

    # Download tools
    tools_dir = APPIMAGE_DIR / "tools"
    tools_dir.mkdir(exist_ok=True)

    appimagetool = tools_dir / "appimagetool"
    linuxdeploy = tools_dir / "linuxdeploy"
    linuxdeploy_plugin_gtk = tools_dir / "linuxdeploy-plugin-gtk"

    if not appimagetool.exists():
        _download_file(APPIMAGE_TOOL_URL, appimagetool)
    if not linuxdeploy.exists():
        _download_file(LINUXDEPLOY_URL, linuxdeploy)
    if not linuxdeploy_plugin_gtk.exists():
        _download_file(LINUXDEPLOY_PLUGIN_GTK_URL, linuxdeploy_plugin_gtk)

    # Make tools executable
    for tool in [appimagetool, linuxdeploy, linuxdeploy_plugin_gtk]:
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)

    # Set environment for linuxdeploy
    env = os.environ.copy()
    env["LINUXDEPLOY_PLUGIN_GTK"] = str(linuxdeploy_plugin_gtk)

    # Run linuxdeploy to fix dependencies
    print("Running linuxdeploy to fix dependencies...")
    _run(
        [
            str(linuxdeploy),
            "--appdir", str(appdir),
            "--plugin", "gtk",
            "--output", "appimage",
        ],
        cwd=APPIMAGE_DIR,
    )

    # Find generated AppImage
    appimage_files = list(APPIMAGE_DIR.glob("*.AppImage"))
    if not appimage_files:
        raise AppImageBuildError("No AppImage file generated")

    # Rename to standard naming convention
    appimage_file = appimage_files[0]
    final_name = f"VeneraNext-{version}-x86_64.AppImage"
    final_path = BUILD_LINUX_DIR / final_name
    appimage_file.rename(final_path)

    print(f"AppImage created: {final_path}")
    print(f"Size: {final_path.stat().st_size / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    try:
        main()
    except AppImageBuildError as error:
        print(f"::error::{error}")
        raise SystemExit(1)
