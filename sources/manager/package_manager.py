import os
import subprocess
import shutil
import argparse

def build_opkg(arch: str):
    """
    Lädt den opkg-Quellcode herunter und kompiliert ihn für die gewünschte Architektur.

    Args:
        arch (str): Zielarchitektur, entweder 'x86_64' oder 'arm64'.
    """
    # Prüfen der Architektur
    if arch not in ["x86_64", "arm64"]:
        raise ValueError("Ungültige Architektur. Nur 'x86_64' oder 'arm64' erlaubt.")
    
    # Arbeitsverzeichnis
    workdir = os.path.abspath("opkg_build")
    os.makedirs(workdir, exist_ok=True)
    
    # opkg Repo URL
    repo_url = "https://git.openwrt.org/project/opkg.git"
    opkg_dir = os.path.join(workdir, "opkg")
    
    # opkg herunterladen
    if not os.path.exists(opkg_dir):
        print("[*] Klone opkg-Repo...")
        subprocess.run(["git", "clone", repo_url, opkg_dir], check=True)
    else:
        print("[*] opkg-Repo existiert bereits, pull updates...")
        subprocess.run(["git", "-C", opkg_dir, "pull"], check=True)
    
    # Compiler bestimmen
    if arch == "x86_64":
        cross = "x86_64-linux-gnu-"
    else:  # arm64
        cross = "aarch64-linux-gnu-"
    
    env = os.environ.copy()
    env["CC"] = cross + "gcc"
    env["LD"] = cross + "ld"
    env["AR"] = cross + "ar"
    env["CFLAGS"] = "-O2"
    
    print(f"[*] Kompiliere opkg für Architektur {arch} mit Cross-Compiler {cross}...")
    
    # Build ausführen
    subprocess.run(["make", "clean"], cwd=opkg_dir, check=True, env=env)
    subprocess.run(["make"], cwd=opkg_dir, check=True, env=env)
    
    # Ergebnis kopieren
    output_bin = os.path.join(opkg_dir, "opkg")
    dest_bin = os.path.join(workdir, f"opkg_{arch}")
    shutil.copy2(output_bin, dest_bin)
    
    print(f"[*] opkg erfolgreich gebaut: {dest_bin}")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="opkg herunterladen und kompilieren")
#     parser.add_argument("--arch", required=True, help="Zielarchitektur: x86_64 oder arm64")
#     args = parser.parse_args()
    
#     build_opkg(args.arch)
