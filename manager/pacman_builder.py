import os
import subprocess
from pathlib import Path
from core.logger import success, info, warning, error

# ──────────────────────────────────────────────
# Pakete, die wir mit Pacman behandeln wollen
# ──────────────────────────────────────────────
PACMAN_PACKAGES = [
    "make",
    "cmake",
    "python",
    "nano",
    "bash",
    "gcc",
    "clang",
    "python-pip"
]

# Mapping der Architektur auf pacman triplet / repo suffix
ARCH_MAPPING = {
    "x86_64": "x86_64",
    "arm64": "aarch64"
}

# ──────────────────────────────────────────────
# Funktion zum Ausführen eines Shell-Kommandos
# ──────────────────────────────────────────────
def run(cmd, cwd=None, env=None):
    info(f"💻 Führe aus: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Fehler beim Ausführen von: {' '.join(cmd)}")


# ──────────────────────────────────────────────
# Funktion zum Installieren der Pakete via Pacman
# ──────────────────────────────────────────────
def build_pacman_packages(args, rootfs_dir: Path):
    arch = args.arch
    if arch not in ARCH_MAPPING:
        raise RuntimeError(f"Unsupported architecture: {arch}")

    arch_suffix = ARCH_MAPPING[arch]
    rootfs_dir.mkdir(parents=True, exist_ok=True)

    info(f"📦 Installiere Pacman-Pakete für Architektur: {arch} in {rootfs_dir}")

    for pkg in PACMAN_PACKAGES:
        try:
            # Pacman Download + Extraktion (ohne Installation im Host)
            cmd_download = [
                "pacman", "-Sw", pkg,
                f"--arch={arch_suffix}", "--cachedir", str(rootfs_dir / "pacman_cache"),
                "--noconfirm"
            ]
            run(cmd_download)

            # Paket ins RootFS extrahieren
            pkg_filename = f"{pkg}.pkg.tar.zst"
            pkg_path = rootfs_dir / "pacman_cache" / pkg_filename
            if not pkg_path.exists():
                warning(f"Paket {pkg_filename} nicht gefunden, überspringe Extraktion.")
                continue

            cmd_extract = [
                "bsdtar", "-xvf", str(pkg_path),
                "-C", str(rootfs_dir)
            ]
            run(cmd_extract)

            success(f"✅ {pkg} erfolgreich in {rootfs_dir} installiert.")

        except Exception as e:
            error(f"❌ Fehler beim Installieren von {pkg}: {e}")
            continue
