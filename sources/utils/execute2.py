import os
import subprocess
from pathlib import Path
from core.logger import success, info, warning, error


def run_command(commands: list[str], cwd: Path | None = None, env: dict | None = None, desc="Befehl ausführen", check_root=False) -> bool:
    """
    Führt einen Befehl aus und zeigt stdout/stderr nach Ausführung.
    Gibt True zurück, wenn erfolgreich, sonst False.
    """
    if check_root and os.geteuid() != 0:
        error(f"Fehler: '{' '.join(commands)}' erfordert Rootrechte.")
        return False

    print(f"\n--- {desc} ---")
    cwd_str = str(cwd) if cwd else None

    try:
        result = subprocess.run(commands, cwd=cwd_str, env=env, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        if result.returncode == 0:
            success(f"✔ '{' '.join(commands)}' erfolgreich abgeschlossen.")
            return True
        else:
            error(f"❌ Fehler bei '{' '.join(commands)}': Exit Code {result.returncode}")
            return False
    except FileNotFoundError:
        error(f"❌ Fehler: Befehl '{commands[0]}' nicht gefunden.")
        return False
    except Exception as e:
        error(f"❌ Unbekannter Fehler bei '{' '.join(commands)}': {e}")
        return False


def run(commands: list[str], cwd: Path | None = None, env: dict | None = None, desc="Befehl ausführen", check_root=False) -> bool:
    """Alias für run_command, bleibt kompatibel."""
    return run_command(commands, cwd, env, desc, check_root)


def run_command_live(commands: list[str], cwd: Path | None = None, env: dict | None = None, desc="Befehl ausführen", check_root=False) -> bool:
    """
    Führt einen Befehl aus, zeigt stdout/stderr live.
    Gibt True zurück bei Erfolg, False bei Fehler.
    """
    if check_root and os.geteuid() != 0:
        error(f"Fehler: '{' '.join(commands)}' erfordert Rootrechte.")
        return False

    print(f"\n--- {desc} ---")
    cwd_str = str(cwd) if cwd else None
    env = env or os.environ.copy()

    try:
        process = subprocess.Popen(
            commands,
            cwd=cwd_str,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        assert process.stdout is not None
        for line in process.stdout:
            print(line.rstrip())

        retcode = process.wait()
        if retcode == 0:
            success(f"✔ '{' '.join(commands)}' erfolgreich abgeschlossen.")
            return True
        else:
            error(f"❌ Fehler: '{' '.join(commands)}' mit Exit-Code {retcode}")
            return False

    except FileNotFoundError:
        error(f"❌ Fehler: Befehl '{commands[0]}' nicht gefunden.")
        return False
    except Exception as e:
        error(f"❌ Unbekannter Fehler bei '{' '.join(commands)}': {e}")
        return False
