#!/usr/bin/env python3
import os
import multiprocessing
from pathlib import Path
import subprocess
from utils.download import download_file, extract_archive
from utils.execute2 import run_command_live
from utils.load import load_config
from core.logger import success, info, warning, error
from manager.opkg import build_opkg
# ──────────────────────────────────────────────
# Host-Tools
# ──────────────────────────────────────────────
HOST_TOOLS = [
    "perl", "python3", "glib2", "pkgconf", "device-mapper",
    "libudev", "libusb", "bash", "util-linux",
    "meson", "ninja", "gpgme", "json-glib", "libsoup", "libdevmapper"
]

PACKAGE_HOST_DEPS = {
    "fwupd": ["libusb"],
    "lvm2": ["device-mapper"],
    "inxi": ["perl"]
}

# ──────────────────────────────────────────────
# Lade alle Pakete
# ──────────────────────────────────────────────
def load_all_packages(configs_dir: Path) -> dict:
    packages = {}

    for host_tool in HOST_TOOLS:
        packages[host_tool] = {
            "name": host_tool,
            "version": "host",
            "urls": [],
            "src_dir": "",
            "deps": [],
            "configure": []
        }

    for cfg_file in (configs_dir / "packages").glob("*.json"):
        conf = load_config(cfg_file)
        conf.setdefault("deps", [])
        conf.setdefault("configure", [])
        name = conf["name"]
        if name in packages:
            warning(f"⚠️ Überschreibe vorhandenes Paket: {name}")
        packages[name] = conf
        if name in PACKAGE_HOST_DEPS:
            for dep in PACKAGE_HOST_DEPS[name]:
                if dep not in conf["deps"]:
                    conf["deps"].append(dep)

    return packages

# ──────────────────────────────────────────────
# Abhängigkeitsauflösung
# ──────────────────────────────────────────────
def resolve_build_order(packages: dict) -> list[str]:
    visited, order = {}, []

    def visit(name: str):
        if name in visited:
            if visited[name] == "temp":
                raise RuntimeError(f"Zirkuläre Abhängigkeit entdeckt bei {name}")
            return
        visited[name] = "temp"
        for dep in packages[name].get("deps", []):
            if dep not in packages:
                raise RuntimeError(f"Unbekannte Abhängigkeit {dep} für Paket {name}")
            visit(dep)
        visited[name] = "perm"
        order.append(name)

    for pkg in packages:
        visit(pkg)
    return order

# ──────────────────────────────────────────────
# Pacman Downloader / Compiler für Arch RootFS
# ──────────────────────────────────────────────
def pacman_download_package(package_name: str, arch: str, download_dir: Path):
    """
    Nutzt pacman-host auf Host, um Quellpakete für Zielarchitektur herunterzuladen
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    info(f"⬇️  Lade Paket {package_name} für {arch}...")
    cmd = [
        "pacman", "-Sp", "--noconfirm",
        "--arch", arch,
    ] + [package_name]
    # pacman -Sp liefert URL, die wir herunterladen
    result = subprocess.run(cmd, capture_output=True, text=True)
    urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    files = []
    for url in urls:
        tarball = download_file([url], download_dir)
        files.append(tarball)
    return files

# ──────────────────────────────────────────────
# Build-Logik wie in deinem System
# ──────────────────────────────────────────────
def build_generic(args, conf, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    name = conf["name"]

    # Spezielle Behandlung für opkg
    if name == "opkg":
        build_opkg(args, conf, work_dir, downloads_dir, rootfs_dir)
        return True  # Build abgeschlossen

    # Host-Tool-Check
    if conf.get("version") == "host":
        info(f"⚡ {conf['name']} ist ein Host-Tool, überspringe Build.")
        return True  # erfolgreich "gebaut"

    name = conf["name"]
    version = conf["version"]
    src_dir = Path(conf["src_dir"].format(version=version))

    info(f"\n=== Baue Paket: {name} {version} ===")

    # Download über pacman falls URLs leer
    if not conf.get("urls"):
        arch = args.arch if args.arch else "x86_64"
        tarballs = pacman_download_package(name, arch, downloads_dir)
    else:
        tarballs = [download_file(conf["urls"], downloads_dir)]

    for tarball in tarballs:
        extract_archive(tarball, work_dir)

    info(f"📂 Quellverzeichnis: {src_dir}")

    # Architektur-Setup
    arch = args.arch if args.arch else "x86_64"
    env = os.environ.copy()
    if arch in ("x86_64", "amd64"):
        host = "x86_64-linux-gnu"
        env["CC"] = "gcc"
        env["CXX"] = "g++"
        arch_str = "x86_64"
    elif arch in ("arm64", "aarch64"):
        host = "aarch64-linux-gnu"
        env["CC"] = "aarch64-linux-gnu-gcc"
        env["CXX"] = "aarch64-linux-gnu-g++"
        arch_str = "aarch64"
    else:
        raise RuntimeError(f"Unsupported architecture: {arch}")

    # Configure
    if conf.get("configure"):
        cmd = [part.replace("{arch}", arch_str).replace("{rootfs}", str(rootfs_dir)) for part in conf["configure"]]
        run_command_live(cmd, cwd=src_dir, env=env, desc=f"{name}: custom configure")
    else:
        configure_script = src_dir / "configure"
        cmake_file = src_dir / "CMakeLists.txt"
        if configure_script.exists():
            cmd = ["./configure", f"--host={host}", "--prefix=/usr"]
            if name == "gcc":
                cmd.append("--disable-multilib")
            run_command_live(cmd, cwd=src_dir, env=env, desc=f"{name}: configure")
        elif cmake_file.exists():
            build_dir = src_dir / "build"
            build_dir.mkdir(exist_ok=True)
            cmd = [
                "cmake", "..",
                f"-DCMAKE_INSTALL_PREFIX=/usr",
                f"-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_C_COMPILER={env['CC']}",
                f"-DCMAKE_CXX_COMPILER={env['CXX']}"
            ]
            run_command_live(cmd, cwd=build_dir, env=env, desc=f"{name}: cmake configure")
        else:
            warning(f"⚠️ Kein configure/CMakeLists.txt gefunden – überspringe configure.")
            build_dir = src_dir

    # Build & Install
    num_cores = multiprocessing.cpu_count()
    make_dir = build_dir if 'build_dir' in locals() else src_dir
    run_command_live(["make", f"-j{num_cores}"], cwd=make_dir, env=env, desc=f"{name}: build")
    run_command_live(["make", f"DESTDIR={rootfs_dir}", "install"], cwd=make_dir, env=env, desc=f"{name}: install")
    success(f"✅ {name} {version} erfolgreich installiert in {rootfs_dir}")

# ──────────────────────────────────────────────
# Alle Pakete bauen
# ──────────────────────────────────────────────
def pacman_build_all(args, configs_dir: Path, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    packages = load_all_packages(configs_dir)
    build_order = resolve_build_order(packages)
    info(f"📦 Build-Reihenfolge: {', '.join(build_order)}")
    failed = []

    for name in build_order:
        conf = packages[name]
        try:
            build_generic(args, conf, work_dir, downloads_dir, rootfs_dir)
        except Exception as e:
            error(f"❌ Fehler beim Bauen von {name}: {e}")
            failed.append(name)
            if not getattr(args, "ignore_errors", False):
                raise
            else:
                warning("➡️ Ignoriere Fehler und fahre fort.")

    if failed:
        error("\n⚠️ Folgende Pakete konnten nicht gebaut werden:")
        for n in failed:
            error(f"  - {n}")
    else:
        success("\n✅ Alle Pakete erfolgreich gebaut!")
