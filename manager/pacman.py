import os
import subprocess
import multiprocessing
from pathlib import Path

from utils.download import download_file, extract_archive
from utils.execute import run_command_live
from utils.load import load_config

from manager.opkg import build_opkg

from core.logger import success, info, warning, error

# ──────────────────────────────────────────────
#  Host-Tools
# ──────────────────────────────────────────────
HOST_TOOLS = [
    "perl", "python3", "glib2", "pkgconf", "device-mapper",
    "libudev", "libusb", "bash", "util-linux", "meson",
    "ninja", "gpgme", "json-glib", "libsoup", "libdevmapper"
]

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
    for host_tool in HOST_TOOLS:
        packages[host_tool] = {
            "name": host_tool,
            "version": "host",
            "urls": [],
            "src_dir": "",
            "deps": [],
            "configure": []
        }

    for cfg_file in (configs_dir / "packages" / "pacman").glob("*.json"):
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
#  Pacman-Integration
# ──────────────────────────────────────────────
class PacmanBuilder:
    def __init__(self, arch: str, download_dir: Path, work_dir: Path, rootfs_dir: Path):
        self.arch = arch
        self.download_dir = download_dir
        self.work_dir = work_dir
        self.rootfs_dir = rootfs_dir
        self.env = os.environ.copy()

        if arch in ("x86_64", "amd64"):
            self.host = "x86_64-unknown-linux-gnu"
            self.env["CC"] = "gcc"
            self.env["CXX"] = "g++"
        elif arch in ("arm64", "aarch64"):
            self.host = "aarch64-unknown-linux-gnu"
            self.env["CC"] = "aarch64-linux-gnu-gcc"
            self.env["CXX"] = "aarch64-linux-gnu-g++"
        else:
            raise RuntimeError(f"Unsupported architecture: {arch}")

        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.rootfs_dir.mkdir(parents=True, exist_ok=True)

    def download_packages(self, packages: list[str]):
        for pkg in packages:
            info(f"⬇️ Download {pkg} via pacman")
            try:
                subprocess.run(
                    ["pacman", "-Sw", "--noconfirm", "--cachedir", str(self.download_dir), pkg],
                    check=True
                )
            except subprocess.CalledProcessError:
                error(f"❌ Fehler beim Download von {pkg}")

    def extract_package(self, pkg_file: Path):
        info(f"📂 Extrahiere {pkg_file.name}")
        subprocess.run(
            ["bsdtar", "-xf", str(pkg_file), "-C", str(self.work_dir)],
            check=True
        )

    def build_package(self, src_dir: Path):
        info(f"\n=== Baue Paket: {src_dir.name} ===")
        configure_script = src_dir / "configure"
        cmake_file = src_dir / "CMakeLists.txt"
        build_dir = src_dir

        try:
            if configure_script.exists():
                cmd = ["./configure", f"--host={self.host}", "--prefix=/usr"]
                run_command_live(cmd, cwd=src_dir, env=self.env, desc=f"{src_dir.name}: configure")
            elif cmake_file.exists():
                build_dir = src_dir / "build"
                build_dir.mkdir(exist_ok=True)
                cmd = [
                    "cmake", "..",
                    f"-DCMAKE_INSTALL_PREFIX=/usr",
                    f"-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_C_COMPILER={self.env['CC']}",
                    f"-DCMAKE_CXX_COMPILER={self.env['CXX']}"
                ]
                run_command_live(cmd, cwd=build_dir, env=self.env, desc=f"{src_dir.name}: cmake configure")
            else:
                warning(f"⚠️ Kein configure/CMakeLists.txt gefunden – überspringe configure.")

            num_cores = multiprocessing.cpu_count()
            run_command_live(["make", f"-j{num_cores}"], cwd=build_dir, env=self.env, desc=f"{src_dir.name}: build")
            run_command_live(["make", f"DESTDIR={self.rootfs_dir}", "install"], cwd=build_dir, env=self.env, desc=f"{src_dir.name}: install")

            success(f"✅ {src_dir.name} gebaut und installiert in {self.rootfs_dir}")

        except Exception as e:
            error(f"❌ Fehler beim Bauen von {src_dir.name}: {e}")
            raise

    def build_them(self, package_names: list[str]):
        # 1️⃣ Download
        self.download_packages(package_names)

        # 2️⃣ Extrahieren + Build
        for pkg_file in self.download_dir.glob("*.pkg.tar.zst"):
            self.extract_package(pkg_file)
            # Annahme: src_dir im work_dir nach Extraktion
            src_dir_guess = self.work_dir / pkg_file.stem
            if not src_dir_guess.exists():
                dirs = [d for d in self.work_dir.iterdir() if d.is_dir()]
                if dirs:
                    src_dir_guess = dirs[0]
                else:
                    warning(f"⚠️ Kein Quellverzeichnis gefunden für {pkg_file.name}, überspringe")
                    continue
            self.build_package(src_dir_guess)

# ──────────────────────────────────────────────
#  Build-Generic erweitert um Pacman-Pakete
# ──────────────────────────────────────────────
def build_generic(args, conf, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    name = conf["name"]

    if name == "opkg":
        build_opkg(args, conf, work_dir, downloads_dir, rootfs_dir)
        return True

    if conf.get("version") == "host":
        info(f"⚡ {name} ist ein Host-Tool, überspringe Build.")
        return True

    # Check ob Pacman-Paket
    if conf.get("source") == "pacman":
        builder = PacmanBuilder(args.arch, downloads_dir, work_dir, rootfs_dir)
        builder.build_all(conf.get("packages", []))
        return True

    # Standard-JSON Build wie vorher
    version = conf["version"]
    src_dir = Path(conf["src_dir"].format(version=version))
    info(f"\n=== Baue Paket: {name} {version} ===")

    try:
        tarball = download_file(conf["urls"], downloads_dir)
        extract_archive(tarball, work_dir)
        info(f"📂 Quellverzeichnis: {src_dir}")

        arch = args.arch if args.arch else "x86_64"
        env = os.environ.copy()
        if arch in ("x86_64", "amd64"):
            host = "x86_64-unknown-linux-gnu"
            env["CC"] = "gcc"
            env["CXX"] = "g++"
        elif arch in ("arm64", "aarch64"):
            host = "aarch64-unknown-linux-gnu"
            env["CC"] = "aarch64-linux-gnu-gcc"
            env["CXX"] = "aarch64-linux-gnu-g++"
        else:
            raise RuntimeError(f"Unsupported architecture: {arch}")

        build_dir = src_dir
        if conf.get("configure"):
            cmd = [part.replace("{arch}", arch).replace("{rootfs}", str(rootfs_dir)) for part in conf["configure"]]
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

        num_cores = multiprocessing.cpu_count()
        make_dir = build_dir if 'build_dir' in locals() else src_dir
        run_command_live(["make", f"-j{num_cores}"], cwd=make_dir, env=env, desc=f"{name}: build")
        run_command_live(["make", f"DESTDIR={rootfs_dir}", "install"], cwd=make_dir, env=env, desc=f"{name}: install")

        success(f"✅ {name} {version} erfolgreich installiert in {rootfs_dir}")
        return True

    except Exception as e:
        error(f"❌ Fehler beim Bauen von {name}: {e}")
        if getattr(args, "ignore_errors", False):
            warning("➡️ Ignoriere Fehler und fahre fort")
            return False
        else:
            raise
