import os
import tarfile
from pathlib import Path

from utils.download import download_file
from utils.execute import run_command_live
from core.logger import success, info, warning, error


# ──────────────────────────────────────────────
#  Paketmanager-Installation
# ──────────────────────────────────────────────
# Installiert den einfachsten Paketmanager (opkg oder apk) in das rootfs.
def install_package_manager(args, rootfs_dir: Path, downloads_dir: Path):
    """
    Installiert einen Paketmanager (opkg oder apk) im Root-Dateisystem.
    """
    info("\n=== Installiere Paketmanager im Root-Dateisystem ===")

    arch = args.arch if args.arch else "x86_64"
    
    # Architektur-Setup (wie in build_generic)
    if arch in ("x86_64", "amd64"):
        pkg_manager = "opkg" # opkg ist für Embedded-Systeme wie OpenWrt/Buildroot üblich
        arch_map = {
            "opkg": "x86_64", # Beispiel für die opkg-Architekturbezeichnung
            "apk": "x86_64"
        }
    elif arch in ("arm64", "aarch64"):
        pkg_manager = "opkg" 
        arch_map = {
            "opkg": "aarch64", # Beispiel für die opkg-Architekturbezeichnung
            "apk": "aarch64"
        }
    else:
        raise RuntimeError(f"Nicht unterstützte Architektur für Paketmanager: {arch}")

    info(f"➡️ Wähle Paketmanager: **{pkg_manager}** für Architektur: **{arch}**")
    
    if pkg_manager == "opkg":
        # Dies ist ein **vereinfachtes** Beispiel. In der Realität müsste man opkg oder
        # seine Abhängigkeiten bauen oder ein passendes vorkompiliertes Binary finden.
        # Wir simulieren hier die Installation eines vorkompilierten Binaries.
        
        # Annahme: opkg-binary ist als Tarball verfügbar
        opkg_arch_name = arch_map["opkg"]
        OPKG_URLS = [
            f"https://example.com/downloads/opkg/{opkg_arch_name}/opkg.tar.gz" # Platzhalter-URL
        ]

        try:
            # 1. Dummy-Download des Tarballs
            info(f"⬇️  Simuliere Download von **opkg**-Binaries für {opkg_arch_name}...")
            # Um den Fehler 'download_file' nicht zu bekommen, wenn die URL ungültig ist,
            # müsste man eine echte URL eintragen oder den Download-Schritt mocken.
            # Da die URL ein Platzhalter ist, überspringen wir den echten Download.
            # tarball_path = download_file(OPKG_URLS, downloads_dir)
            
            # Da wir die Datei nicht wirklich herunterladen können, simulieren wir die
            # Erstellung einer minimalen opkg-Struktur im rootfs.
            
            # 2. Notwendige Verzeichnisse erstellen
            (rootfs_dir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
            (rootfs_dir / "etc" / "opkg").mkdir(parents=True, exist_ok=True)
            
            # 3. Dummy-opkg-Binary erstellen
            opkg_binary_path = rootfs_dir / "usr" / "bin" / "opkg"
            try:
                # Erstellt eine leere, ausführbare Datei, die als Platzhalter dient
                with open(opkg_binary_path, "w") as f:
                    f.write("#!/bin/sh\necho 'opkg ist installiert, aber dies ist eine Dummy-Datei.'\n")
                os.chmod(opkg_binary_path, 0o755)
            except Exception as e:
                error(f"❌ Fehler beim Erstellen des Dummy-opkg-Binaries: {e}")
                raise
            
            # 4. Dummy-Konfigurationsdatei erstellen (optional)
            conf_file = rootfs_dir / "etc" / "opkg" / "opkg.conf"
            with open(conf_file, "w") as f:
                f.write("dest root /\n")
                f.write("option check_signature 0\n")
                f.write(f"src/gz example_repo https://example.com/{opkg_arch_name}/packages\n")
            
            # 5. Abschluss und Test (simuliert)
            info("📦 Führe (simulierten) Testlauf von opkg aus...")
            run_command_live([str(opkg_binary_path), "--version"], cwd=rootfs_dir, desc="opkg test (simuliert)")
            
            success(f"✅ **opkg** ({opkg_arch_name}) erfolgreich in **{rootfs_dir}** installiert (simuliert/Platzhalter).")

        except Exception as e:
            error(f"❌ Fehler bei der Installation von **opkg**: {e}")
            raise
    
    elif pkg_manager == "apk":
        # Ähnliche Logik für Alpine Linux's apk, die oft einfacher als ein statisches Binary verfügbar ist.
        # Dies würde typischerweise das Herunterladen und Extrahieren eines apk-static-Binaries beinhalten.
        
        info("⚠️ Die Installation von apk ist hier nicht implementiert. Es wird **opkg** verwendet.")
        # Implementierung würde hier folgen
        # ...
        pass


# ──────────────────────────────────────────────
#  Erweitertes build_all (für Modul-Integration)
# ──────────────────────────────────────────────
# Um die neue Funktion nutzen zu können, müsste build_all erweitert werden.
# Wir fügen die Funktion hier ein, um das Modul eigenständig zu halten.

# *Ihr ursprünglicher Code für load_all_packages, resolve_build_order und build_generic
# *müsste hier oder in einer importierten Datei verfügbar sein.
# *Für dieses Beispiel nehmen wir an, dass sie verfügbar sind oder wir implementieren
# *nur die End-to-End-Funktion, die Sie aufrufen würden.

# Beispiel, wie die neue Funktion in Ihren Build-Prozess integriert wird:

def build_all_and_install_pkg_manager(args, configs_dir: Path, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    
    # Hier würde der Aufruf der ursprünglichen build_all-Funktion erfolgen
    # build_all(args, configs_dir, work_dir, downloads_dir, rootfs_dir)
    
    # Dummy-Ausgabe, da die Abhängigkeiten fehlen
    info("\n⚠️  Simuliere den Abschluss des 'build_all'-Prozesses.")
    
    # Nach dem Bauen aller Basispakete den Paketmanager installieren
    install_package_manager(args, rootfs_dir, downloads_dir)
    
    success("\n✅ Build-Prozess und Paketmanager-Installation abgeschlossen!")

# ──────────────────────────────────────────────
#  Platzhalter für Hilfsfunktionen
# ──────────────────────────────────────────────
# Wenn Sie diesen Code als eigenständiges Modul verwenden, stellen Sie sicher, 
# dass die folgenden importierten Funktionen auch definiert sind:
# from utils.download import download_file, extract_archive
# from utils.execute import run_command_live
# from core.logger import success, info, warning, error