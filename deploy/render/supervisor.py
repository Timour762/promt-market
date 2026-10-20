"""Run migrations, then supervise all processes in one Render web service."""
from __future__ import annotations

import os
import json
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import MutableMapping
from urllib.parse import urlsplit


POLL_SECONDS = 0.1
SHUTDOWN_SECONDS = 10.0


def prepare_environment(environ: MutableMapping[str, str]) -> None:
    """Use Render's assigned HTTPS origin unless an explicit one was supplied."""
    value = environ.get("PUBLIC_WEB_URL") or environ.get("RENDER_EXTERNAL_URL", "")
    try:
        parts = urlsplit(value)
        hostname = parts.hostname or ""
        # Console-provided public hostnames must be plain HTTPS origins.
        valid_host = bool(hostname) and all(
            re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
            for label in hostname.split(".")
        )
        valid = (
            parts.scheme == "https" and valid_host
            and parts.username is None and parts.password is None
            and parts.path in ("", "/") and not parts.query and not parts.fragment
            and not any(character.isspace() for character in value) and "\\" not in value
            and (parts.port is None or 1 <= parts.port <= 65535)
            and not parts.netloc.endswith(":")
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Set PUBLIC_WEB_URL or RENDER_EXTERNAL_URL to a valid HTTPS origin.")
    origin = value.rstrip("/")
    if not environ.get("PUBLIC_WEB_URL"):
        environ["PUBLIC_WEB_URL"] = origin
    if not environ.get("ALLOWED_ORIGINS"):
        environ["ALLOWED_ORIGINS"] = json.dumps([origin])
    if not environ.get("AUTH_ALLOWED_ORIGINS"):
        environ["AUTH_ALLOWED_ORIGINS"] = origin


@dataclass(frozen=True)
class Service:
    name: str
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str] | None = None


class Supervisor:
    def __init__(self) -> None:
        self.stop_signal: int | None = None
        self.children: list[tuple[str, subprocess.Popen]] = []

    def request_stop(self, signum: int, _frame=None) -> None:
        self.stop_signal = signum

    def start(self, service: Service) -> subprocess.Popen:
        # Inherit stdout/stderr directly; never print commands or environment values.
        process = subprocess.Popen(
            service.command,
            cwd=service.cwd,
            env=service.env,
            start_new_session=(os.name == "posix"),
        )
        self.children.append((service.name, process))
        print(f"Started {service.name}.", flush=True)
        return process

    def run(self, migration: Service, services: tuple[Service, ...]) -> int:
        try:
            process = self.start(migration)
            while process.poll() is None:
                if self.stop_signal is not None:
                    return 128 + self.stop_signal
                time.sleep(POLL_SECONDS)
            if process.returncode != 0:
                print("Database migrations failed; application was not started.", file=sys.stderr, flush=True)
                return 1
            self.children.remove((migration.name, process))

            for service in services:
                if self.stop_signal is not None:
                    return 128 + self.stop_signal
                self.start(service)

            while self.stop_signal is None:
                for name, child in self.children:
                    if child.poll() is not None:
                        print(f"{name} exited unexpectedly; stopping service.", file=sys.stderr, flush=True)
                        return 1
                time.sleep(POLL_SECONDS)
            return 128 + self.stop_signal
        except OSError:
            print("Unable to start an application process; stopping service.", file=sys.stderr, flush=True)
            return 1
        finally:
            self.shutdown()

    @staticmethod
    def signal_child(process: subprocess.Popen, *, force: bool = False) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
            elif force:
                process.kill()
            else:
                process.terminate()
        except ProcessLookupError:
            pass

    def shutdown(self) -> None:
        for _, process in reversed(self.children):
            self.signal_child(process)
        deadline = time.monotonic() + SHUTDOWN_SECONDS
        for _, process in reversed(self.children):
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                self.signal_child(process, force=True)
        for _, process in self.children:
            process.wait()


def main() -> int:
    try:
        prepare_environment(os.environ)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    try:
        port = int(os.environ.get("PORT", "10000"))
        if not 1024 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("PORT must be an integer between 1024 and 65535.", file=sys.stderr)
        return 1

    backend = Path("/app/backend")
    frontend_env = os.environ.copy()
    frontend_env.update({
        "HOSTNAME": "0.0.0.0", "PORT": str(port), "BACKEND_URL": "http://127.0.0.1:8107",
        "AUTH_CLIENT_IP_SOURCE": "render",
    })
    supervisor = Supervisor()
    signal.signal(signal.SIGTERM, supervisor.request_stop)
    signal.signal(signal.SIGINT, supervisor.request_stop)
    return supervisor.run(
        Service("migrations", (sys.executable, "-m", "alembic", "upgrade", "head"), backend),
        (
            Service("API", (sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8107", "--no-access-log"), backend),
            Service("mail worker", (sys.executable, "-m", "app.mail_worker"), backend),
            Service("web", ("node", "server.js"), Path("/app/web"), frontend_env),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())

