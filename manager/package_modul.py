import os
import multiprocessing
from pathlib import Path

from utils.download import download_file, extract_archive
from utils.execute import run_command_live
from utils.load import load_config

from manager.opkg import build_opkg

from core.logger import success, info, warning, error


# ──────────────────────────────────────────────
#  Host-Tools, die nicht gebaut werden
# ──────────────────────────────────────────────
# Host-Tools: Werden nicht gebaut, dienen nur als bekannte Abhängigkeiten
# Host-Tools: werden nicht gebaut, dienen nur als bekannte Abhängigkeiten
HOST_TOOLS = [
    "perl",
    "python3",
    "glib2",
    "pkgconf",
    "device-mapper",
    "libudev",
    "libusb",
    "bash",
    "util-linux",
    "meson",
    "ninja",
    "gpgme",
    "json-glib",
    "libsoup",
    "libdevmapper"
]



# ──────────────────────────────────────────────
#  Spezielle Host-Abhängigkeiten pro Paket
# ──────────────────────────────────────────────
PACKAGE_HOST_DEPS = {
    "fwupd": ["libusb"],
    "lvm2": ["device-mapper"],
    "inxi": ["perl"]
}


# ──────────────────────────────────────────────
#  Pakete laden + Host-Abhängigkeiten mergen
# ──────────────────────────────────────────────
def load_all_packages(configs_dir: Path) -> dict:
    packages = {}

    # Zuerst Host-Tools als virtuelle Pakete anlegen
    for host_tool in HOST_TOOLS:
        packages[host_tool] = {
            "name": host_tool,
            "version": "host",
            "urls": [],
            "src_dir": "",
            "deps": [],
            "configure": []
        }

    # Jetzt JSON-Pakete laden
    for cfg_file in (configs_dir / "packages").glob("*.json"):
        conf = load_config(cfg_file)

        # Basisabsicherung
        conf.setdefault("deps", [])
        conf.setdefault("configure", [])

        # Paketname muss eindeutig sein
        name = conf["name"]
        if name in packages:
            warning(f"⚠️  Überschreibe vorhandenes Paket: {name}")
        packages[name] = conf

        # Host-Abhängigkeiten mergen
        if name in PACKAGE_HOST_DEPS:
            for dep in PACKAGE_HOST_DEPS[name]:
                if dep not in conf["deps"]:
                    conf["deps"].append(dep)

    return packages


# ──────────────────────────────────────────────
#  Abhängigkeitsauflösung
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
#  Generischer Builder (mit Ignore-Errors Unterstützung)
# ──────────────────────────────────────────────
def build_generic(args, conf, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    # Host-Tool-Check
    
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

    try:
        # Download & Entpacken
        tarball = download_file(conf["urls"], downloads_dir)
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
        build_dir = src_dir
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

        # Build & Install
        num_cores = multiprocessing.cpu_count()
        make_dir = build_dir if 'build_dir' in locals() else src_dir

        run_command_live(["make", f"-j{num_cores}"], cwd=make_dir, env=env, desc=f"{name}: build")
        run_command_live(["make", f"DESTDIR={rootfs_dir}", "install"], cwd=make_dir, env=env, desc=f"{name}: install")

        success(f"✅ {name} {version} erfolgreich installiert in {rootfs_dir}")
        return True

    except Exception as e:
        error(f"❌ Fehler beim Bauen von {name}: {e}")
        if getattr(args, "ignore_errors", False):
            warning(f"➡️ Ignoriere Fehler und fahre mit dem nächsten Paket fort.")
            return False
        else:
            raise


# ──────────────────────────────────────────────
#  Alle Pakete in Abhängigkeitsreihenfolge bauen
# ──────────────────────────────────────────────
def build_all(args, configs_dir: Path, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    packages = load_all_packages(configs_dir)
    build_order = resolve_build_order(packages)
    info(f"📦 Build-Reihenfolge: {', '.join(build_order)}")

    failed = []

    for name in build_order:
        conf = packages[name]
        result = build_generic(args, conf, work_dir, downloads_dir, rootfs_dir)
        if not result:
            failed.append(name)

    if failed:
        error("\n⚠️ Folgende Pakete konnten nicht gebaut werden:")
        for n in failed:
            error(f"  - {n}")
    else:
        success("\n✅ Alle Pakete erfolgreich gebaut!")
