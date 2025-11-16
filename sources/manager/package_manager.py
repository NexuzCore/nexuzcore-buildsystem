import os
from pathlib import Path
import shutil

from utils.download import download_file, extract_archive
from utils.execute2 import run_command_live
from core.logger import success, info, warning, error




def build_opkg(args, conf, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    """
    Baut opkg als generisches Paket für x86_64 oder arm64.
    Wird in build_generic aufgerufen.
    """

    if conf.get("version") == "host":
        info(f"⚡ {conf['name']} ist ein Host-Tool, überspringe Build.")
        return

    name = conf["name"]
    version = conf["version"]

    # Arbeitsverzeichnis für opkg
    opkg_dir = work_dir / "opkg"
    os.makedirs(work_dir, exist_ok=True)

    # Repo klonen oder updaten
    repo_url = "https://git.yoctoproject.org/opkg"
    if not opkg_dir.exists():
        info(f"[*] Klone opkg-Repo nach {opkg_dir}...")
        run_command_live(["git", "clone", repo_url, str(opkg_dir)], cwd=work_dir)
    else:
        warning("[*] opkg-Repo existiert bereits, pull updates...")
        run_command_live(["git", "-C", str(opkg_dir), "pull"], cwd=work_dir)

    # Architektur & Compiler
    arch = args.arch if args.arch else "x86_64"
    env = os.environ.copy()
    if arch == "x86_64":
        cross = "x86_64-linux-gnu-"
    elif arch in ("arm64", "aarch64"):
        cross = "aarch64-linux-gnu-"
    else:
        raise RuntimeError(f"Unsupported architecture: {arch}")

    env["CC"] = cross + "gcc"
    env["LD"] = cross + "ld"
    env["AR"] = cross + "ar"
    env["CFLAGS"] = "-O2"

    info(f"[*] Kompiliere opkg für Architektur {arch} mit Cross-Compiler {cross}...")

    # Clean & Build
    run_command_live(["make", "clean"], cwd=opkg_dir, env=env, desc=f"{name}: clean")
    run_command_live(["make"], cwd=opkg_dir, env=env, desc=f"{name}: build")

    # Ergebnis kopieren
    output_bin = opkg_dir / "opkg"
    if not output_bin.exists():
        error("❌ opkg-Binary nicht gefunden nach Build!")
        return

    dest_bin = work_dir / f"opkg_{arch}"
    shutil.copy2(output_bin, dest_bin)

    # Optional ins RootFS kopieren
    rootfs_bin_dir = rootfs_dir / "usr" / "bin"
    rootfs_bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest_bin, rootfs_bin_dir)

    success(f"✅ opkg erfolgreich gebaut: {dest_bin}")
    success(f"✅ opkg ins RootFS kopiert: {rootfs_bin_dir}")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="opkg herunterladen und kompilieren")
#     parser.add_argument("--arch", required=True, help="Zielarchitektur: x86_64 oder arm64")
#     args = parser.parse_args()
    
#     build_opkg(args.arch)
