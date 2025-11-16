import os, subprocess, sys

from pathlib import Path


from core.logger import success, info, warning, error






def run_command(commands: list[str], cwd: Path | None = None, env: dict | None = None, desc="Befehl ausführen", check_root=False):
    """_summary_

    Args:
        commands (list[str]): _description_
        cwd (Path | None, optional): _description_. Defaults to None.
        env (dict | None, optional): _description_. Defaults to None.
        desc (str, optional): _description_. Defaults to "Befehl ausführen".
        check_root (bool, optional): _description_. Defaults to False.
    """
    
    
    if check_root and os.geteuid() != 0:
        error(f"Fehler: '{' '.join(commands)}' erfordert Rootrechte.")
        sys.exit(1)

    print(f"\n--- {desc} ---")
    cwd_str = str(cwd) if cwd else None

    try:
        # Live-Ausgabe aktivieren
        result = subprocess.run(commands, cwd=cwd_str, env=env, text=True)
        if result.returncode != 0:
            error(f"Fehler bei '{' '.join(commands)}': Exit Code {result.returncode}")
            sys.exit(result.returncode)
        success(f"✔ '{' '.join(commands)}' erfolgreich abgeschlossen.")
    except FileNotFoundError:
        error(f"Fehler: Befehl '{commands[0]}' nicht gefunden.")
        sys.exit(1)






def run(commands: list[str], cwd: Path | None = None, env: dict | None = None, desc="Befehl ausführen", check_root=False) -> bool:
    """_summary_

    Args:
        commands (list[str]): _description_
        cwd (Path | None, optional): _description_. Defaults to None.
        env (dict | None, optional): _description_. Defaults to None.
        desc (str, optional): _description_. Defaults to "Befehl ausführen".
        check_root (bool, optional): _description_. Defaults to False.

    Returns:
        bool: _description_
    """

    if check_root and os.geteuid() != 0:
        error(f"Fehler: '{' '.join(commands)}' erfordert Rootrechte.")
        return False

    print(f"\n--- {desc} ---")
    cwd_str = str(cwd) if cwd else None

    try:
        result = subprocess.run(commands, cwd=cwd_str, env=env, capture_output=True, text=True, check=True)
        if result.stdout: print(result.stdout.strip())
        if result.stderr: print(result.stderr.strip())
        success(f"✔ '{' '.join(commands)}' erfolgreich abgeschlossen.")
        return True
    except FileNotFoundError:
        error(f"Fehler: Befehl '{commands[0]}' nicht gefunden.")
        return False
    except subprocess.CalledProcessError as e:
        error(f"Fehler bei '{' '.join(commands)}': Exit Code {e.returncode}")
        if e.stdout: print(e.stdout.strip())
        if e.stderr: print(e.stderr.strip())
        return False






def run_command_live(commands: list[str], cwd: Path | None = None, env: dict | None = None, desc="Befehl ausführen", check_root=False):
    """
    Führt einen Befehl aus, zeigt stdout/stderr live, unterstützt viele Kerne.
    """
    
    if check_root and os.geteuid() != 0:
        error(f"Fehler: '{' '.join(commands)}' erfordert Rootrechte.")
        sys.exit(1)

    print(f"\n--- {desc} ---")
    cwd_str = str(cwd) if cwd else None
    env = env or os.environ.copy()

    # Prozess starten
    process = subprocess.Popen(
        commands,
        cwd=cwd_str,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Zeilenweise Puffern
    )

    # Zeilenweise ausgeben
    assert process.stdout is not None
    for line in process.stdout:
        print(line.rstrip())

    retcode = process.wait()
    if retcode != 0:
        error(f"\nFehler: '{' '.join(commands)}' mit Exit-Code {retcode}")
        sys.exit(retcode)
    success(f"✔ '{' '.join(commands)}' erfolgreich abgeschlossen.")
