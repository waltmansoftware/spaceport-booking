#!/usr/bin/env python3
"""Set up and run the Django and Vite development servers."""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MINIMUM_PYTHON = (3, 12)


def supports_python(command):
    try:
        result = subprocess.run(
            command + ["-c", "import sys; raise SystemExit(sys.version_info < (3, 12))"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except OSError:
        return False


def supports_venv(command):
    try:
        result = subprocess.run(
            command
            + [
                "-c",
                "import sys; raise SystemExit(sys.version_info < (3, 12) or sys.prefix == sys.base_prefix)",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except OSError:
        return False


def find_python():
    candidates = [[sys.executable]]
    if os.name == "nt":
        candidates.append(["py", "-3.12"])
    candidates.extend([["python3.12"], ["python3"]])
    for command in candidates:
        if supports_python(command):
            return command
    return None


def require_node():
    node = shutil.which("node")
    if node:
        result = subprocess.run(
            [
                node,
                "-e",
                "const [a,b]=process.versions.node.split('.').map(Number);"
                "process.exit(a>22||(a===22&&b>=18)?0:1)",
            ]
        )
        if result.returncode == 0:
            return
    raise RuntimeError("Node.js 22.18 or newer is required.")


def ensure_pip():
    pip_check = subprocess.run(
        [
            str(VENV_PYTHON),
            "-c",
            "import pip, sys; from pathlib import Path; "
            "p=Path(pip.__file__).resolve(); v=Path(sys.prefix).resolve(); "
            "raise SystemExit(sys.prefix == sys.base_prefix or v not in p.parents)",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if pip_check.returncode != 0:
        print("Bootstrapping pip in the virtual environment...", flush=True)
        subprocess.run([str(VENV_PYTHON), "-m", "ensurepip", "--upgrade"], cwd=ROOT, check=True)


def prepare_environment():
    if not supports_venv([str(VENV_PYTHON)]):
        python = find_python()
        if not python:
            raise RuntimeError("Python 3.12 or newer is required.")
        print("Creating Python environment...", flush=True)
        subprocess.run(python + ["-m", "venv", str(VENV)], cwd=ROOT, check=True)
        if not supports_venv([str(VENV_PYTHON)]):
            raise RuntimeError("Python could not create a valid virtual environment at .venv.")

    require_node()
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm was not found next to the Node.js installation.")

    ensure_pip()
    print("Checking dependencies...", flush=True)
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", "requirements.txt"],
        cwd=ROOT,
        check=True,
    )

    lockfile = FRONTEND / "package-lock.json"
    install_marker = FRONTEND / "node_modules" / ".package-lock.json"
    if not install_marker.exists() or lockfile.stat().st_mtime > install_marker.stat().st_mtime:
        subprocess.run([npm, "--prefix", str(FRONTEND), "ci"], cwd=ROOT, check=True)

    print("Preparing database...", flush=True)
    subprocess.run([str(VENV_PYTHON), "manage.py", "migrate", "--noinput"], cwd=ROOT, check=True)
    tools = ROOT / ".tools"
    tools.mkdir(exist_ok=True)
    seed_path = tools / "local-seed.json"
    print("Replacing local data with a fresh randomized seed...", flush=True)
    with seed_path.open("w", encoding="utf-8") as seed_file:
        subprocess.run([str(VENV_PYTHON), "seed.py"], cwd=ROOT, check=True, stdout=seed_file, text=True)
    subprocess.run([str(VENV_PYTHON), "manage.py", "load_seed", str(seed_path)], cwd=ROOT, check=True)
    return npm


def stop_process_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def require_available_ports():
    unavailable = []
    for port in (8000, 5173):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            try:
                listener.bind(("127.0.0.1", port))
            except OSError:
                unavailable.append(str(port))
    if unavailable:
        raise RuntimeError(
            "Development port{} {} already in use. Stop the existing local server and try again.".format(
                "s" if len(unavailable) > 1 else "",
                ", ".join(unavailable),
            )
        )


def run_servers(npm):
    process_options = {}
    if os.name == "nt":
        process_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        process_options["start_new_session"] = True

    print("\nStarting Pacific Spaceport at http://127.0.0.1:5173", flush=True)
    print("Press Ctrl-C to stop both servers.\n", flush=True)
    backend = subprocess.Popen(
        [str(VENV_PYTHON), "manage.py", "runserver", "127.0.0.1:8000"],
        cwd=ROOT,
        **process_options
    )
    frontend = subprocess.Popen(
        [npm, "--prefix", str(FRONTEND), "run", "dev"],
        cwd=ROOT,
        **process_options
    )
    processes = [("Django", backend), ("Vite", frontend)]
    previous_handlers = {}

    def request_shutdown(_signal_number, _frame):
        raise KeyboardInterrupt

    shutdown_signals = [signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):
        shutdown_signals.append(signal.SIGHUP)
    for shutdown_signal in shutdown_signals:
        previous_handlers[shutdown_signal] = signal.getsignal(shutdown_signal)
        signal.signal(shutdown_signal, request_shutdown)

    print(
        "Development supervisor is running "
        "(Django PID {}, Vite PID {}).".format(backend.pid, frontend.pid),
        flush=True,
    )
    print("This terminal remains active; press Ctrl-C to stop everything.", flush=True)
    try:
        while all(process.poll() is None for _, process in processes):
            time.sleep(0.5)
        name, process = next((item for item in processes if item[1].poll() is not None))
        print("{} exited unexpectedly with status {}.".format(name, process.returncode), file=sys.stderr)
        return process.returncode or 1
    except KeyboardInterrupt:
        return 0
    finally:
        print("\nStopping Django and Vite...", flush=True)
        for _, process in processes:
            stop_process_tree(process)
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        for shutdown_signal, previous_handler in previous_handlers.items():
            signal.signal(shutdown_signal, previous_handler)
        print("Development servers stopped.", flush=True)


def main():
    os.chdir(ROOT)
    try:
        require_available_ports()
        npm = prepare_environment()
        return run_servers(npm)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print("Error: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
