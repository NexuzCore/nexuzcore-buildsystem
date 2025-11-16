import os
import shutil
import subprocess
from pathlib import Path

from utils.download import download_file, extract_archive
from core.logger import success, info, warning, error


# ──────────────────────────────────────────────
#  OPKG Builder für BusyBox RootFS
# ──────────────────────────────────────────────

OPKG_URL = "https://downloads.openwrt.org/releases/packages-24.10/x86_64/base/opkg_2024.10.16~38eccbb1-r1_x86_64.ipk"
OPKG_CONF_TEMPLATE = """\
src/gz base http://downloads.openwrt.org/releases/22.03.8/packages/x86_64/base
dest root /
lists_dir ext /var/lib/opkg/lists
option overlay_root /overlay
option check_signature 0
"""


def install_opkg(rootfs_dir: Path, work_dir: Path):
    """
    Installiert opkg in das gegebene BusyBox RootFS.
    """
    info(f"🔧 Installiere opkg in RootFS: {rootfs_dir}")

    # Download
    tarball = download_file([OPKG_URL], work_dir)
    info(f"📦 OPKG Tarball heruntergeladen: {tarball} nach: {work_dir}")

 

    # Prüfen ob sbin/bin existiert
    bin_dir = rootfs_dir / "usr" / "bin"
    sbin_dir = rootfs_dir / "usr" / "sbin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    sbin_dir.mkdir(parents=True, exist_ok=True)

    # opkg Dateien kopieren
    opkg_files = ["usr/bin/opkg", "usr/lib/opkg"]
    for f in opkg_files:
        src = work_dir / f
        if not src.exists():
            warning(f"⚠️ Datei nicht gefunden: {src}")
            continue
        dest = rootfs_dir / f
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)

    # Konfigurationsordner
    etc_opkg = rootfs_dir / "etc" / "opkg"
    etc_opkg.mkdir(parents=True, exist_ok=True)
    conf_file = etc_opkg / "opkg.conf"
    conf_file.write_text(OPKG_CONF_TEMPLATE)
    info(f"⚙️ OPKG Konfiguration erstellt: {conf_file}")

    # Datenbank-Ordner
    var_opkg = rootfs_dir / "var" / "lib" / "opkg"
    var_opkg.mkdir(parents=True, exist_ok=True)
    info(f"📂 OPKG Datenbank-Verzeichnis: {var_opkg}")

    success("✅ OPKG erfolgreich ins RootFS eingebunden!")


def test_opkg(rootfs_dir: Path):
    """
    Führt einen einfachen OPKG Test im RootFS aus.
    """
    info("⚡ Teste OPKG Installation im RootFS...")
    opkg_bin = rootfs_dir / "usr" / "bin" / "opkg"
    if not opkg_bin.exists():
        error(f"OPKG Binary nicht gefunden: {opkg_bin}")
        return

    try:
        subprocess.run([str(opkg_bin), "help"], check=True)
        success("✅ OPKG Test erfolgreich – Binary funktioniert!")
    except subprocess.CalledProcessError as e:
        error(f"❌ OPKG Test fehlgeschlagen: {e}")
