import requests
import tarfile
import zipfile
from pathlib import Path
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.console import Console
from core.logger import success, info, warning, error

console = Console()


def download_file(urls, dest_dir: Path, timeout: int = 60) -> Path:
    """
    Lädt eine Datei via HTTP/HTTPS herunter.
    Unterstützt mehrere Mirror-URLs als Fallback.
    Zeigt modernes TUI mit ETA, Fortschritt, Dateigröße und Zielpfad.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(urls, str):
        urls = [urls]

    last_error = None
    for url in urls:
        filename = url.split("/")[-1]
        dest = dest_dir / filename

        if dest.exists():
            warning(f"{filename} bereits vorhanden, überspringe Download.")
            return dest

        info(f"Versuche Download von {url} ...")
        try:
            with requests.get(url, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))

                progress = Progress(
                    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                    BarColumn(bar_width=None),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    TextColumn("[green]{task.fields[path]}"),
                )

                with progress:
                    task = progress.add_task(
                        "download",
                        filename=filename,
                        path=str(dest_dir),
                        total=total,
                    )

                    with open(dest, "wb") as f:
                        for chunk in response.iter_content(chunk_size=1024 * 32):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

            success(f"Download abgeschlossen: {dest}")
            return dest

        except Exception as e:
            error(f"⚠️ Fehler beim Download von {url}: {e}")
            last_error = e
            continue

    raise RuntimeError(f"Download fehlgeschlagen. Letzter Fehler: {last_error}")


def extract_archive(archive_path: Path, extract_to: Path) -> Path:
    """
    Entpackt ein Archiv in ein Zielverzeichnis.
    Unterstützt: .tar.gz, .tgz, .tar.bz2, .tar.xz, .tar, .zip
    Zeigt Fortschritt mit ETA für große Archive.
    """
    archive_path = Path(archive_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    name = archive_path.name.lower()
    info(f"Entpacke {archive_path} nach {extract_to} ...")

    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}"),
        BarColumn(bar_width=None),
        TextColumn("[green]{task.completed}/{task.total} Dateien"),
        TimeRemainingColumn(),
    )

    with progress:
        if name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar")):
            mode = "r"
            if name.endswith(".tar.gz") or name.endswith(".tgz"):
                mode = "r:gz"
            elif name.endswith(".tar.bz2"):
                mode = "r:bz2"
            elif name.endswith(".tar.xz"):
                mode = "r:xz"

            with tarfile.open(archive_path, mode) as tar:
                members = tar.getmembers()
                task = progress.add_task("extract", filename=archive_path.name, total=len(members))
                for member in members:
                    tar.extract(member, path=extract_to)
                    progress.update(task, advance=1)

        elif name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                members = zip_ref.namelist()
                task = progress.add_task("extract", filename=archive_path.name, total=len(members))
                for member in members:
                    zip_ref.extract(member, path=extract_to)
                    progress.update(task, advance=1)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")

    success(f"Entpackt: {archive_path.name} → {extract_to}")

    dirs = [d for d in extract_to.iterdir() if d.is_dir()]
    if len(dirs) == 1:
        return dirs[0]
    return extract_to


def download_and_extract(urls, dest_dir: Path, extract_to: Path) -> Path:
    """
    Kombinierter Ablauf: Download + Entpacken.
    """
    downloaded_file = download_file(urls, dest_dir)
    extracted_path = extract_archive(downloaded_file, extract_to)
    return extracted_path
