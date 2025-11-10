#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# create.py
# Erstellt Workspace und RootFS-Struktur für BusyBox

import os
import sys
import stat
import shutil

from pathlib import Path

# -----------------------------
# Basisverzeichnisse
# -----------------------------
app_dir = Path(__file__).parent.resolve()
work_dir = Path("work")

downloads_dir = work_dir / "downloads"
build_dir = work_dir / "build"
output_dir = work_dir / "output"
rootfs_dir = build_dir / "rootfs"
bootfs_dir = build_dir / "bootfs"

workspace_dirs = [
    work_dir, downloads_dir, build_dir, output_dir, rootfs_dir, bootfs_dir
]

# -----------------------------
# RootFS-Unterverzeichnisse
# -----------------------------
rootfs_subdirs = [
    "bin", "sbin", "lib", "lib64", "boot", "dev", "proc", "sys", "tmp", "mnt", 
    "media", "opt", "home", "root", "run", "root/.ssh",
    "etc", "etc/init.d", "etc/network", "etc/rc.d", "etc/skel", "etc/ssh",
    "etc/systemd", "etc/default", "etc/sysconfig",
    "var", "var/log", "var/run", "var/lock", "var/tmp", "var/spool", "var/lib",
    "usr/bin", "usr/sbin", "usr/lib", "usr/include", "usr/share/man", "usr/share/doc", "usr/share/locale",
    "usr/local/bin", "usr/local/sbin", "usr/local/lib", "usr/local/etc", "usr/local/share",
    "srv/www"
]

# -----------------------------
# Minimal /etc Konfig-Dateien
# -----------------------------
etc_files = {
    "inittab": """::sysinit:/etc/init.d/rcS
::askfirst:/bin/sh
::ctrlaltdel:/bin/umount -a -r
::shutdown:/bin/umount -a -r
""",
    "fstab": """proc    /proc   proc    defaults    0   0
sysfs   /sys    sysfs   defaults    0   0
tmpfs   /tmp    tmpfs   defaults    0   0
devtmpfs /dev   devtmpfs defaults   0   0
""",
    "hostname": "minilinux\n",
    "hosts": """127.0.0.1   localhost
::1         localhost
""",
    "issue": "Minimal Linux \\n \\l\n",
    "motd": "Willkommen zu MiniLinux\n",
    "network/interfaces": """auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
""",
    "resolv.conf": "nameserver 8.8.8.8\n",
    "init.d/rcS": """#!/bin/sh
echo "[rcS] Mounting pseudo filesystems..."
mount -t proc none /proc || echo "[rcS] Warning: /proc mount failed"
mount -t sysfs none /sys || echo "[rcS] Warning: /sys mount failed"
mount -t devtmpfs devtmpfs /dev || echo "[rcS] Warning: /dev mount failed"
mount -t tmpfs tmpfs /tmp || echo "[rcS] Warning: /tmp mount failed"
mount -t tmpfs tmpfs /run || echo "[rcS] Warning: /run mount failed"
mkdir -p /run/lock

if [ -x /sbin/mdev ]; then
    echo "/sbin/mdev" > /proc/sys/kernel/hotplug 2>/dev/null
    /sbin/mdev -s
fi

ifconfig lo up
echo "[rcS] Boot complete."
exec /bin/sh
""",
    "etc/profile": """# /etc/profile
export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
PS1='\\u@\\h:\\w\\$ '
"""
}

# -----------------------------
# BusyBox init
# -----------------------------
init_script_content = """#!/bin/sh
echo "Starting minimal BusyBox init..."
mount -t proc none /proc
mount -t sysfs none /sys
echo "Root filesystem ready."
exec /bin/sh
"""

# -----------------------------
# Funktionen
# -----------------------------

def create_directories(extra_dir: str | None = None):
    """Erstellt Workspace und RootFS-Verzeichnisse"""
    print("[INFO] Creating main directories...")
    for d in workspace_dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Created {d}")

    print("[INFO] Creating rootfs directories...")
    for sub in rootfs_subdirs:
        path = rootfs_dir / sub
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o755)
        print(f"[INFO] Created {path}")
    
    if extra_dir:
        extra_path = Path(extra_dir)
        extra_path.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Created extra directory {extra_path}")

    print("[INFO] All directories created.")


def create_etc_files():
    """Erstellt alle minimalen /etc Konfig-Dateien"""
    etc_path = rootfs_dir / "etc"
    print("[INFO] Creating /etc configuration files...")
    for filename, content in etc_files.items():
        rel_path = filename.replace("etc/", "") if filename.startswith("etc/") else filename
        file_path = etc_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        if file_path.name == "rcS" or file_path.suffix == ".sh":
            file_path.chmod(0o755)
        print(f"[INFO] Created {file_path}")


def create_dev_nodes():
    """Erstellt Device Nodes; simuliert, falls keine Rootrechte"""
    dev_path = rootfs_dir / "dev"
    dev_path.mkdir(parents=True, exist_ok=True)
    print("[INFO] Creating device nodes in /dev...")

    devices = [
        ("null", stat.S_IFCHR, 1, 3, 0o666),
        ("zero", stat.S_IFCHR, 1, 5, 0o666),
        ("console", stat.S_IFCHR, 5, 1, 0o666),
        ("tty", stat.S_IFCHR, 5, 0, 0o666),
        ("tty0", stat.S_IFCHR, 4, 0, 0o666),
        ("tty1", stat.S_IFCHR, 4, 1, 0o666),
        ("random", stat.S_IFCHR, 1, 8, 0o444),
        ("urandom", stat.S_IFCHR, 1, 9, 0o444),
    ]

    for name, typ, major, minor, perms in devices:
        node_path = dev_path / name
        if not node_path.exists():
            try:
                os.mknod(node_path, typ | perms, os.makedev(major, minor))
                print(f"[INFO] Created device node {node_path}")
            except PermissionError:
                node_path.touch()
                node_path.chmod(perms)
                print(f"[WARN] Permission denied; created simulated device node {node_path}")

    (dev_path / "pts").mkdir(exist_ok=True)
    print("[INFO] Created /dev/pts directory")


def create_busybox_init():
    """Erstellt init Skript für BusyBox"""
    init_path = rootfs_dir / "init"
    init_path.write_text(init_script_content)
    init_path.chmod(0o755)
    print(f"[INFO] Created BusyBox init script at {init_path}")


def create_symlinks():
    """Erstellt Standard-Symlinks /sbin/init und /bin/sh zu BusyBox"""
    busybox_path = rootfs_dir / "bin/busybox"
    if busybox_path.exists():
        (rootfs_dir / "sbin/init").symlink_to("../bin/busybox")
        (rootfs_dir / "bin/sh").symlink_to("busybox")
        print("[INFO] BusyBox symlinks created")
    else:
        print("[WARN] BusyBox not found; symlinks skipped")


def set_rootfs_permissions():
    """Setzt Berechtigungen für RootFS"""
    print(f"[INFO] Setting permissions for {rootfs_dir}...")

    for dirpath, _, filenames in os.walk(rootfs_dir):
        path = Path(dirpath)
        if path.name not in ["tmp", "run", "lock", "log", "dev"]:
            path.chmod(0o755)

        for file in filenames:
            f = path / file
            if f.suffix == ".sh" or f.name == "rcS":
                f.chmod(0o755)
            else:
                f.chmod(0o644)

    # Spezielle Verzeichnisse
    for d in [rootfs_dir / "tmp", rootfs_dir / "var/tmp"]:
        if d.exists():
            d.chmod(0o1777)
    for d in [rootfs_dir / "var/log", rootfs_dir / "var/run", rootfs_dir / "var/lock"]:
        if d.exists():
            d.chmod(0o777)
    if (rootfs_dir / "dev").exists():
        (rootfs_dir / "dev").chmod(0o755)
    rootfs_dir.chmod(0o755)
    print("[INFO] Permissions set.")



def copy_qemu_user_static(arch: str, qemu_dir: Path | None = None):
    """
    Kopiert die passenden QEMU user-static Binärdateien ins RootFS, 
    damit cross-arch chroot / BusyBox Shell funktioniert.
    
    :param rootfs: Path zum RootFS
    :param arch: Zielarchitektur, z.B. 'arm64', 'arm', 'x86_64'
    :param qemu_dir: Optionales Verzeichnis, in dem die QEMU-Binärdateien liegen
    """
    
    print("Console > Copying Qemu- Shell Emulation File to RootFS!!!")
    
    
    
    if qemu_dir is None:
        qemu_dir = Path("/usr/bin")  # Standardpfad unter Linux, ggf. anpassen
    
    qemu_map = {
        "arm64": "qemu-aarch64-static",
        "arm": "qemu-arm-static",
        "x86_64": "qemu-x86_64-static",
        "i386": "qemu-i386-static",
    }
    
    qemu_bin_name = qemu_map.get(arch)
    if not qemu_bin_name:
        print(f"[WARN] Keine QEMU-Binärdatei für Architektur {arch} gefunden.")
        return
    
    src = qemu_dir / qemu_bin_name
    dest = rootfs_dir / "usr/bin" / qemu_bin_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    if not src.exists():
        print(f"[WARN] QEMU-Binärdatei {src} existiert nicht. Bitte installieren!")
        return
    
    
    shutil.copy2(src, dest)
    dest.chmod(0o755)
    print(f"[INFO] QEMU-Binärdatei {qemu_bin_name} nach {dest} kopiert.")
