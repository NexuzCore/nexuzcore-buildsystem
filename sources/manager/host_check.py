import shutil
from core.logger import error, success, info

# Diese Liste kommt aus configs/packages/host_tools/
REQUIRED_HOST_TOOLS = [
    "bash",
    "perl",
    "glib2",
    "libusb",
    "python3",
    "util-linux",
    "device-mapper"
]

ARCH_PACKAGES_MAP = {
    "bash": "bash",
    "perl": "perl",
    "glib2": "glib2",
    "libusb": "libusb",
    "python3": "python",
    "util-linux": "util-linux",
    "device-mapper": "device-mapper"
}

def check_host_prerequisites(exit_on_fail=True):
    missing = []
    for tool in REQUIRED_HOST_TOOLS:
        # Suche nach ausführbarer Datei oder prüfe mit spezifischer Methode (z.B. Header-Prüfung ggf. extra)
        if tool == "glib2":
            # Für glib2, checke pkg-config
            if shutil.which("pkg-config") and shutil.which("glib-compile-schemas"):
                continue
        if shutil.which(tool):
            continue
        missing.append(tool)

    if missing:
        packages = [ARCH_PACKAGES_MAP[x] for x in missing]
        error("Es fehlen folgende Build-Host Tools:\n  " + ", ".join(missing))
        error("Installiere sie unter Arch Linux mit:")
        print("\n  sudo pacman -S --needed " + " ".join(packages) + "\n")
        if exit_on_fail:
            exit(1)
        return False
    success("Alle benötigten Host-Tools sind installiert.")
    return True

# if __name__ == "__main__":
#     check_host_prerequisites()