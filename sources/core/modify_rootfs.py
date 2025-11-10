import os
import shutil

from pathlib import Path
from utils.execute import run_command_live

def cpy(qemu_bin_name, rootfs_dir):
    target = Path(rootfs_dir) / "usr/bin" / qemu_bin_name
    print(f"Copying {qemu_bin_name} to {target}")
    run_command_live(["sudo", "cp", f"/usr/bin/{qemu_bin_name}", str(target)])

def chroot(busybox_src_dir, rootfs_dir, arch: str):
    qemu_map = {
        "arm64": "qemu-aarch64-static",
        "arm": "qemu-arm-static",
        "x86_64": "qemu-x86_64-static",
        "i386": "qemu-i386-static",
    }

    qemu_bin_name = qemu_map.get(arch)
    if qemu_bin_name:
        cpy(qemu_bin_name, rootfs_dir)
    else:
        print(f"[WARN] Keine QEMU-Binärdatei für Architektur {arch} gefunden.")

    # Mount FileSystems
    for src, target, fstype, opts in [
        ("/proc", "proc", "proc", None),
        ("/sys", "sys", "sysfs", None),
        ("/dev", "dev", None, "--bind"),
        ("/dev/pts", "dev/pts", None, "--bind"),
    ]:
        mount_target = Path(rootfs_dir) / target
        cmd = ["sudo", "mount"]
        if opts:
            cmd.append(opts)
        if fstype:
            cmd += ["-t", fstype]
        cmd += [src, str(mount_target)]
        run_command_live(cmd)

    # Chroot
    # chroot_cmd = ["sudo", "chroot", rootfs_dir]
    # if qemu_bin_name:
    #     chroot_cmd.append(f"/usr/bin/{qemu_bin_name}")
    # chroot_cmd.append("/bin/sh")

    # run_command_live(
    #     chroot_cmd,
    #     cwd=rootfs_dir,
    #     desc="BusyBox oldconfig (non-interaktiv)"
    # )
    
    run_command_live(["sudo", "chroot", str(rootfs_dir), "/bin/sh"])




def chroot_with_qemu(rootfs_dir: Path, arch: str):
    """
    Kopiert die passenden QEMU-Emulatoren ins RootFS, setzt die Rechte
    und startet ein interaktives Chroot über QEMU.
    
    rootfs_dir : Path -> Pfad zum RootFS
    arch       : str  -> Zielarchitektur, z.B. 'arm64', 'arm', 'x86_64', 'i386'
    """
    
    qemu_map = {
        "arm64": "qemu-aarch64-static",
        "arm": "qemu-arm-static",
        "x86_64": "qemu-x86_64-static",
        "i386": "qemu-i386-static",
    }
    
    qemu_bin = qemu_map.get(arch)
    if not qemu_bin:
        print(f"[ERROR] Keine QEMU-Binärdatei für Architektur '{arch}' gefunden.")
        return
    
    qemu_src = Path("/usr/bin") / qemu_bin
    qemu_dst = Path(rootfs_dir) / "usr/bin" / qemu_bin
    
    if not qemu_src.exists():
        print(f"[ERROR] QEMU-Binary {qemu_src} existiert nicht. Bitte 'qemu-user-static' installieren.")
        return
    
    # Zielverzeichnis sicherstellen
    qemu_dst.parent.mkdir(parents=True, exist_ok=True)
    
    # QEMU kopieren
    shutil.copy2(qemu_src, qemu_dst)
    
    # Rechte setzen (chmod +x)
    qemu_dst.chmod(qemu_dst.stat().st_mode | stat.S_IEXEC)
    
    print(f"[INFO] {qemu_bin} erfolgreich nach {qemu_dst} kopiert und ausführbar gesetzt.")
    
    # Mounten der notwendigen pseudo-filesystems
    for src, target, fstype, opts in [
        ("/proc", "proc", "proc", None),
        ("/sys", "sys", "sysfs", None),
        ("/dev", "dev", None, "--bind"),
        ("/dev/pts", "dev/pts", None, "--bind"),
    ]:
        mount_target = Path(rootfs_dir) / target
        mount_target.mkdir(parents=True, exist_ok=True)
        cmd = ["sudo", "mount"]
        if opts:
            cmd.append(opts)
        if fstype:
            cmd += ["-t", fstype]
        cmd += [src, str(mount_target)]
        run_command_live(cmd)
    
    # Interaktives Chroot starten
    chroot_cmd = ["sudo", "chroot", str(rootfs_dir), f"/usr/bin/{qemu_bin}", "/bin/sh"]
    print(f"[INFO] Starte interaktives Chroot für Architektur '{arch}'...")
    run_command_live(chroot_cmd, cwd=str(rootfs_dir), interactive=True)


def unmount_rootfs(rootfs_dir):
    """Unmount all previously mounted filesystems in rootfs_dir"""
    mounts = [
        Path(rootfs_dir) / "dev/pts",
        Path(rootfs_dir) / "dev",
        Path(rootfs_dir) / "sys",
        Path(rootfs_dir) / "proc",
    ]

    for mnt in mounts:
        run_command_live(["sudo", "umount", "-lf", str(mnt)])