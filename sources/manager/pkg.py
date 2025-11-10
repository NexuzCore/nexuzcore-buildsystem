import os
import multiprocessing
import pathlib
import json



from pathlib import Path
from utils.download import download_file, extract_archive
from utils.execute import run_command_live
from utils.load import load_config   # <--- hinzufügen


def load_package_config(configs_dir: Path, name: str) -> dict:
    return load_config(configs_dir / "packages" / f"{name}.json")

def load_all_packages(configs_dir: Path) -> dict:
    packages = {}
    for cfg_file in (configs_dir / "packages").glob("*.json"):
        conf = load_config(cfg_file)
        packages[conf["name"]] = conf
    return packages


def build_generic(args, conf, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    version = conf["version"]
    src_dir_template = conf["src_dir"]
    src_dir = Path(src_dir_template.format(version=version))

    print(f"\n=== Baue Paket: {conf['name']} {version} ===")

    tarball = download_file(conf["urls"], downloads_dir)
    extracted_dir = extract_archive(tarball, work_dir)
    print(f"Console > Quellverzeichnis: {src_dir}")

    # Cross-Compile Env
    env = os.environ.copy()
    arch = args.arch if args.arch else "x86_64"
    prefix = "aarch64-linux-gnu-" if arch in ("arm64", "aarch64") else ""
    env["CC"] = f"{prefix}gcc"
    env["CXX"] = f"{prefix}g++"

    # Configure falls vorhanden
    configure_script = src_dir / "configure"
    if configure_script.exists():
        cmd = ["./configure", f"--host={arch}-linux-gnu", "--prefix=/usr"]
        if "configure" in conf:
            cmd.extend(conf["configure"])
        run_command_live(cmd, cwd=src_dir, env=env, desc=f"{conf['name']}: configure")

    # Build & Install
    num_cores = multiprocessing.cpu_count()
    run_command_live(["make", f"-j{num_cores}"], cwd=src_dir, env=env, desc=f"{conf['name']}: build")
    run_command_live(["make", f"DESTDIR={rootfs_dir}", "install"], cwd=src_dir, env=env, desc=f"{conf['name']}: install")

    print(f"✅ {conf['name']} {version} erfolgreich installiert in {rootfs_dir}")


def resolve_build_order(packages: dict) -> list[str]:
    """Berechnet die Build-Reihenfolge anhand der deps-Felder (Topological Sort)."""
    visited = {}
    order = []

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

def build_pkgconf(args, conf, urls, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    version = conf["version"]
    src_dir_template = conf["src_dir"]    
    src_dir = Path(src_dir_template.format(version=version))
    print(f"\n=== Baue Paket: {conf['name']} {version} ===")

    tarball = download_file(urls, downloads_dir)
    extracted_dir = extract_archive(tarball, work_dir)

    # subdirs = [d for d in extracted_dir.iterdir() if d.is_dir()]
    # src_dir = subdirs[0] if len(subdirs) == 1 else extracted_dir
    print(f"Console > Quellverzeichnis: {src_dir}")

    env = os.environ.copy()
    arch = args.arch if args.arch else "x86_64"
    if arch in ("arm64", "aarch64"):
        arch = "aarch64"
        prefix = "aarch64-linux-gnu-"
    else:
        prefix = ""

    env["CC"] = f"{prefix}gcc"
    env["CXX"] = f"{prefix}g++"

    run_command_live(
        ["./configure", f"--host={arch}-linux-gnu", "--prefix=/usr"],
        cwd=src_dir,
        env=env,
        desc="pkgconf: configure"
    )

    num_cores = multiprocessing.cpu_count()
    run_command_live(
        ["make", f"-j{num_cores}"],
        cwd=src_dir,
        env=env,
        desc="pkgconf: build"
    )
    run_command_live(
        ["make", f"DESTDIR={rootfs_dir}", "install"],
        cwd=src_dir,
        env=env,
        desc="pkgconf: install"
    )

    print(f"✅ {conf['name']} {version} erfolgreich installiert in {rootfs_dir}")


def build_pkg_config(args, conf, urls, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    version = conf["version"]
    src_dir_template = conf["src_dir"]    
    src_dir = Path(src_dir_template.format(version=version))
    print(f"\n=== Baue Paket: {conf['name']} {version} ===")

    tarball = download_file(urls, downloads_dir)
    extracted_dir = extract_archive(tarball, work_dir)


    print(f"Console > Quellverzeichnis: {src_dir}")

    env = os.environ.copy()
    arch = args.arch if args.arch else "x86_64"
    if arch in ("arm64", "aarch64"):
        arch = "aarch64"
        prefix = "aarch64-linux-gnu-"
    else:
        prefix = ""

    env["CC"] = f"{prefix}gcc"
    env["CXX"] = f"{prefix}g++"

    run_command_live(
        [
            "./configure",
            f"--host={arch}-linux-gnu",
            "--prefix=/usr",
            "--with-internal-glib"
        ],
        cwd=src_dir,
        env=env,
        desc="pkg-config: configure"
    )

    num_cores = multiprocessing.cpu_count()
    run_command_live(
        ["make", f"-j{num_cores}"],
        cwd=src_dir,
        env=env,
        desc="pkg-config: build"
    )
    run_command_live(
        ["make", f"DESTDIR={rootfs_dir}", "install"],
        cwd=src_dir,
        env=env,
        desc="pkg-config: install"
    )

    print(f"✅ {conf['name']} {version} erfolgreich installiert in {rootfs_dir}")


def build_ncurses(args, conf, urls, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    version = conf["version"]
    src_dir_template = conf["src_dir"]    
    src_dir = Path(src_dir_template.format(version=version))

    print(f"\n=== Baue Paket: {conf['name']} {version} ===")

    tarball = download_file(urls, downloads_dir)
    extracted_dir = extract_archive(tarball, work_dir)

    # subdirs = [d for d in extracted_dir.iterdir() if d.is_dir()]
    # src_dir = subdirs[0] if len(subdirs) == 1 else extracted_dir
    print(f"Console > Quellverzeichnis: {src_dir}")

    # Cross‑Compile Env
    env = os.environ.copy()
    arch = args.arch if args.arch else "x86_64"
    if arch in ("arm64", "aarch64"):
        arch = "aarch64"
        prefix = "aarch64-linux-gnu-"
    else:
        prefix = ""

    env["CC"] = f"{prefix}gcc"
    env["CXX"] = f"{prefix}g++"

    # Configure mit Wide‑Char und Termlib
    run_command_live(
    ["./configure", f"--host={arch}-linux-gnu", "--prefix=/usr",
     "--with-shared", "--without-debug", "--enable-widec",
     "--with-termlib", "--enable-pc-files", "--with-cxx-shared",
     "--disable-stripping"],
    cwd=src_dir, env=env, desc="ncurses: configure"
)


    # Build & Install
    num_cores = multiprocessing.cpu_count()
    run_command_live(
        ["make", f"-j{num_cores}"],
        cwd=src_dir,
        env=env,
        desc=f"{conf['name']}: build"
    )
    run_command_live(
        ["make", f"DESTDIR={rootfs_dir}", "install"],
        cwd=src_dir,
        env=env,
        desc=f"{conf['name']}: install"
    )

    print(f"✅ {conf['name']} {version} erfolgreich installiert in {rootfs_dir}")


def build_package(args, conf, urls, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    """Download, Extract, Configure, Compile and Install a single package into RootFS"""
    version = conf["version"]
    src_dir_template = conf["src_dir"]    
    src_dir = Path(src_dir_template.format(version=version))

    # Architektur / Cross-Compile vorbereiten
    cross_compile = {}
    arch = args.arch if args.arch else "x86_64"
    cross_compile["arch"] = arch
    if arch == "x86_64":
        cross_compile["compiler_prefix"] = ""
    elif arch in ("arm64", "aarch64"):
        cross_compile["arch"] = "aarch64"  # Autotools-kompatibel
        cross_compile["compiler_prefix"] = "aarch64-linux-gnu-"

    downloads_dir.mkdir(parents=True, exist_ok=True)
    rootfs_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Baue Paket: {conf['name']} {version} ===")

    # Download & Extract
    tarball = download_file(urls, downloads_dir)
    extracted_dir = extract_archive(tarball, work_dir)

    # Source-Verzeichnis bestimmen
    # subdirs = [d for d in extracted_dir.iterdir() if d.is_dir()]
    # src_dir = subdirs[0] if len(subdirs) == 1 else extracted_dir
    print(f"Console > Quellverzeichnis: {src_dir}")

    # Cross-Compile Env
    env = os.environ.copy()
    env["ARCH"] = cross_compile["arch"]
    if cross_compile["arch"] != "x86_64":
        env["CROSS_COMPILE"] = cross_compile.get("compiler_prefix", "")
    env["CC"] = f"{cross_compile.get('compiler_prefix','')}gcc"
    env["CXX"] = f"{cross_compile.get('compiler_prefix','')}g++"
    env["CFLAGS"] = cross_compile.get("cflags", "")
    env["LDFLAGS"] = cross_compile.get("ldflags", "")

    # Configure (falls vorhanden)
    configure_script = src_dir / "configure"
    if configure_script.exists():
        run_command_live(
            ["./configure", f"--host={cross_compile['arch']}-linux-gnu", "--prefix=/usr"],
            cwd=src_dir,
            env=env,
            desc=f"{conf['name']}: configure"
        )

    # Build mit allen Cores
    num_cores = multiprocessing.cpu_count()
    run_command_live(
        ["make", f"-j{num_cores}"],
        cwd=src_dir,
        env=env,
        desc=f"{conf['name']}: build"
    )

    # Install ins RootFS
    run_command_live(
        ["make", f"DESTDIR={rootfs_dir}", "install"],
        cwd=src_dir,
        env=env,
        desc=f"{conf['name']}: install"
    )

    print(f"✅ {conf['name']} {version} erfolgreich installiert in {rootfs_dir}")



def build_all(args, configs_dir: Path, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    """Baut alle Pakete anhand der deps-Felder in packages.json, fährt bei Fehlern fort"""
    config = load_config(configs_dir / "packages.json")
    packages = config["packages"]

    build_order = resolve_build_order(packages)
    print(f"📦 Build-Reihenfolge: {', '.join(build_order)}")

    failed = []

    for name in build_order:
        pkg = packages[name]
        conf = {
            "name": name,
            "version": pkg["version"],
            "src_dir": pkg["src_dir"]
        }

        try:
            if name == "pkgconf":
                build_pkgconf(args, conf, pkg["urls"], work_dir, downloads_dir, rootfs_dir)
            elif name == "pkg-config":
                build_pkg_config(args, conf, pkg["urls"], work_dir, downloads_dir, rootfs_dir)
            elif name == "ncurses":
                build_ncurses(args, conf, pkg["urls"], work_dir, downloads_dir, rootfs_dir)
            else:
                build_package(args, conf, pkg["urls"], work_dir, downloads_dir, rootfs_dir)
        except Exception as e:
            print(f"❌ Fehler beim Bauen von {name}: {e}")
            failed.append(name)
            continue  # mit dem nächsten Paket weitermachen

    if failed:
        print("\n⚠️ Folgende Pakete konnten nicht gebaut werden:")
        for name in failed:
            print(f"  - {name}")
    else:
        print("\n✅ Alle Pakete erfolgreich gebaut!")


def build_all_old(args, configs_dir: Path, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    """Baut alle Pakete in der richtigen Reihenfolge"""
    config = load_config(configs_dir / "packages.json")
    packages = config["packages"]

    # 1. pkg-config
    pkg = packages["pkg-config"]
    pkg_conf = {"name": "pkg-config", "version": pkg["version"], "src_dir": pkg["src_dir"]}
    build_pkg_config(args, pkg_conf, pkg["urls"], work_dir, downloads_dir, rootfs_dir)

    # 2. ncurses
    nc = packages["ncurses"]
    nc_conf = {"name": "ncurses", "version": nc["version"], "src_dir": nc["src_dir"]}
    build_ncurses(args, nc_conf, nc["urls"], work_dir, downloads_dir, rootfs_dir)

    # 3. gcc
    gcc = packages["gcc"]
    gcc_conf = {"name": "gcc", "version": gcc["version"], "src_dir": gcc["src_dir"]}
    build_package(args, gcc_conf, gcc["urls"], work_dir, downloads_dir, rootfs_dir)

    # 4. python3
    py = packages["python3"]
    py_conf = {"name": "python3", "version": py["version"], "src_dir": py["src_dir"]}
    build_package(args, py_conf, py["urls"], work_dir, downloads_dir, rootfs_dir)

    # 5. restliche Tools
    for name in ("make", "bash", "nano", "opkg"):
        pkg = packages[name]
        conf = {"name": name, "version": pkg["version"], "src_dir": pkg["src_dir"]}
        build_package(args, conf, pkg["urls"], work_dir, downloads_dir, rootfs_dir)



def build(args, work_dir: Path, downloads_dir: Path, rootfs_dir: Path):
    """Baut alle Pakete in der richtigen Reihenfolge"""
    build_ncurses(args, ncurses_conf, packages["ncurses"], work_dir, downloads_dir, rootfs_dir)
    for conf in (make_conf, nano_conf, bash_conf):
        build_package(args, conf, packages[conf["name"]], work_dir, downloads_dir, rootfs_dir)
