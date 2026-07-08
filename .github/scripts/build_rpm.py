#!/usr/bin/env python3
"""Build RPM package for VeneraNext Flutter application."""

import argparse
import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBSPEC_PATH = ROOT / "pubspec.yaml"
BUILD_LINUX_DIR = ROOT / "build" / "linux"
BUNDLE_DIR = BUILD_LINUX_DIR / "x64" / "release" / "bundle"
RPM_DIR = BUILD_LINUX_DIR / "rpm"
RPM_BUILD_DIR = RPM_DIR / "rpmbuild"


class RPMBuildError(RuntimeError):
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
        raise RPMBuildError(f"pubspec.yaml does not contain {key}")
    return _clean_value(match.group("value"))


def _rpm_version(pubspec_version: str) -> tuple[str, str]:
    version, separator, build = pubspec_version.partition("+")
    if not separator:
        build = "1"
    return version, build


def _create_spec_file(
    name: str,
    version: str,
    release: str,
    description: str,
    homepage: str,
) -> str:
    return f"""Name:           venera-next
Version:        {version}
Release:        {release}%{{?dist}}
Summary:        A comic app

License:        GPL-3.0
URL:            {homepage}
Source0:        venera-next-%{{version}}.tar.gz

Requires:       gtk3
Requires:       webkit2gtk4.1

%description
VeneraNext is a comic reader application built with Flutter.

%prep
%setup -q -n venera-next-%{{version}}

%build
# No build needed, pre-built binary

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/lib/venera-next/lib
mkdir -p $RPM_BUILD_ROOT/usr/lib/venera-next/data
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/usr/share/applications
mkdir -p $RPM_BUILD_ROOT/usr/share/icons/hicolor/256x256/apps

# Copy application files
cp -a venera-next $RPM_BUILD_ROOT/usr/lib/venera-next/
cp -a lib/* $RPM_BUILD_ROOT/usr/lib/venera-next/lib/
cp -a data/* $RPM_BUILD_ROOT/usr/lib/venera-next/data/

# Create symlink in /usr/bin
ln -s /usr/lib/venera-next/venera-next $RPM_BUILD_ROOT/usr/bin/venera-next

# Copy desktop file
cp venera-next.desktop $RPM_BUILD_ROOT/usr/share/applications/

# Copy icon
cp venera-next.png $RPM_BUILD_ROOT/usr/share/icons/hicolor/256x256/apps/

%files
%license LICENSE
/usr/lib/venera-next
/usr/lib/venera-next/*
/usr/bin/venera-next
/usr/share/applications/venera-next.desktop
/usr/share/icons/hicolor/256x256/apps/venera-next.png

%changelog
* %(date "+%a %b %d %Y") VeneraNext <https://github.com/CyrilPeng/venera-next> - {version}-{release}
- Build RPM package
"""


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


def _run(command: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RPM package for VeneraNext")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Prepare RPM build tree without building",
    )
    args = parser.parse_args()

    # Read version from pubspec.yaml
    text = PUBSPEC_PATH.read_text(encoding="utf-8")
    version = _top_level_value(text, "version")
    description = _top_level_value(text, "description")
    homepage = _top_level_value(text, "homepage")

    rpm_version, rpm_release = _rpm_version(version)

    print(f"Building RPM package for VeneraNext v{version}")

    # Check if Flutter build exists
    if not BUNDLE_DIR.exists():
        raise RPMBuildError(
            f"Flutter bundle directory not found: {BUNDLE_DIR}\n"
            "Please run 'flutter build linux' first."
        )

    # Prepare RPM build tree
    if RPM_DIR.exists():
        shutil.rmtree(RPM_DIR)

    rpm_build_dir = RPM_DIR / "rpmbuild"
    sources_dir = rpm_build_dir / "SOURCES"
    specs_dir = rpm_build_dir / "SPECS"
    build_dir = rpm_build_dir / "BUILD"
    buildroot_dir = rpm_build_dir / "BUILDROOT"
    rpms_dir = rpm_build_dir / "RPMS"
    srpms_dir = rpm_build_dir / "SRPMS"

    for d in [sources_dir, specs_dir, build_dir, buildroot_dir, rpms_dir, srpms_dir]:
        d.mkdir(parents=True)

    # Create source tarball
    print("Creating source tarball...")
    tarball_name = f"venera-next-{rpm_version}"
    tarball_path = sources_dir / f"{tarball_name}.tar.gz"

    with tarfile.open(tarball_path, "w:gz") as tar:
        # Add bundle contents
        for item in BUNDLE_DIR.rglob("*"):
            arcname = f"{tarball_name}/{item.relative_to(BUNDLE_DIR)}"
            tar.add(item, arcname=arcname)

        # Add desktop file
        desktop_content = _create_desktop_file()
        desktop_file_path = ROOT / "debian" / "gui" / "venera-next.desktop"
        if desktop_file_path.exists():
            tar.add(desktop_file_path, arcname=f"{tarball_name}/venera-next.desktop")
        else:
            import io

            info = tarfile.TarInfo(name=f"{tarball_name}/venera-next.desktop")
            data = desktop_content.encode("utf-8")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        # Add icon
        icon_src = ROOT / "debian" / "gui" / "venera-next.png"
        if icon_src.exists():
            tar.add(icon_src, arcname=f"{tarball_name}/venera-next.png")
        else:
            alt_icons = [
                ROOT / "assets" / "app_icon.png",
                ROOT / "assets" / "Venera-Next.svg",
            ]
            for alt_icon in alt_icons:
                if alt_icon.exists():
                    tar.add(alt_icon, arcname=f"{tarball_name}/venera-next.png")
                    break

        # Add LICENSE if exists
        license_file = ROOT / "LICENSE"
        if license_file.exists():
            tar.add(license_file, arcname=f"{tarball_name}/LICENSE")

    # Create spec file
    spec_content = _create_spec_file(
        name="venera-next",
        version=rpm_version,
        release=rpm_release,
        description=description,
        homepage=homepage,
    )
    spec_file = specs_dir / "venera-next.spec"
    spec_file.write_text(spec_content, encoding="utf-8")

    if args.prepare_only:
        print(f"Prepared RPM build tree at {rpm_build_dir}")
        return

    # Build RPM
    print("Building RPM package...")
    _run(
        [
            "rpmbuild",
            "--nodeps",
            "--define", f"_topdir {rpm_build_dir}",
            "-ba", str(spec_file),
        ],
        cwd=RPM_DIR,
    )

    # Find generated RPM
    rpm_files = list(rpms_dir.rglob("*.rpm"))
    if not rpm_files:
        raise RPMBuildError("No RPM file generated")

    # Copy to build output
    rpm_file = rpm_files[0]
    final_name = f"venera-next-{rpm_version}-{rpm_release}.x86_64.rpm"
    final_path = BUILD_LINUX_DIR / final_name
    shutil.copy2(rpm_file, final_path)

    print(f"RPM package created: {final_path}")
    print(f"Size: {final_path.stat().st_size / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    try:
        main()
    except RPMBuildError as error:
        print(f"::error::{error}")
        raise SystemExit(1)
