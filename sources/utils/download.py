import requests, tarfile, zipfile



from pathlib import Path
from tqdm import tqdm

from core.logger import success, info, warning, error


def download_file(urls, dest_dir: Path, timeout: int = 60) -> Path:
    """
    Lädt eine Datei via HTTP/HTTPS herunter.
    - Akzeptiert entweder einen einzelnen URL (str)
      oder eine Liste von URLs (list[str]) als Mirror-Fallback.
    """
    
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Falls nur ein String übergeben wurde → in Liste packen
    if isinstance(urls, str):
        urls = [urls]

    last_error = None
    for url in urls:
        filename = url.split("/")[-1]
        dest = dest_dir / filename

        # Bereits vorhanden?
        if dest.exists():
            warning(f"Console > {filename} bereits vorhanden, überspringe Download.")
            return dest

        info(f"Console > Versuche Download von {url} ...")
        try:
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))

            with open(dest, "wb") as f, tqdm(
                desc=f"Downloading {filename}",
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
                    bar.update(len(chunk))

            success(f"Console > Download abgeschlossen: {dest}")
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
    """
    
    
    archive_path = Path(archive_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    name = archive_path.name.lower()

    if name.endswith((".tar.gz", ".tgz")):
        mode = "r:gz"
        with tarfile.open(archive_path, mode) as tar:
            tar.extractall(path=extract_to)
    elif name.endswith(".tar.bz2"):
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=extract_to)
    elif name.endswith(".tar.xz"):
        with tarfile.open(archive_path, "r:xz") as tar:
            tar.extractall(path=extract_to)
    elif name.endswith(".tar"):
        with tarfile.open(archive_path, "r:") as tar:
            tar.extractall(path=extract_to)
    elif name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(path=extract_to)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")

    success(f"Console > Entpackt: {archive_path.name} → {extract_to}")

    # Falls nur ein Unterordner enthalten ist, direkt diesen zurückgeben
    dirs = [d for d in extract_to.iterdir() if d.is_dir()]
    if len(dirs) == 1:
        return dirs[0]
    return extract_to
