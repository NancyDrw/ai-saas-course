#!/usr/bin/env python3
"""Run the same release checks locally and in GitHub Actions."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE_NAME = "intima-preflight"
REQUIRED_FILES = (
    "Dockerfile.render",
    "render.yaml",
    ".env.example",
    "requirements.txt",
    "admin/package.json",
    "admin/package-lock.json",
)


def run(*command: str) -> None:
    """Run one check and stop immediately on failure."""
    print(f"\n$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def tracked_secret_files() -> list[str]:
    """Return tracked dotenv files other than the safe template."""
    result = subprocess.run(
        ["git", "ls-files", "--", ".env", ".env.*"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        path
        for path in result.stdout.splitlines()
        if path and path != ".env.example"
    ]


def check_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"Missing production files: {', '.join(missing)}")


def main() -> int:
    try:
        print("PREFLIGHT: checking production files", flush=True)
        check_required_files()

        secrets = tracked_secret_files()
        if secrets:
            raise RuntimeError(
                "Tracked dotenv files are not allowed: " + ", ".join(secrets)
            )

        run("git", "diff", "--check")
        run("npm", "ci", "--prefix", "admin")
        run("npm", "run", "build", "--prefix", "admin")
        run("docker", "build", "-f", "Dockerfile.render", "-t", IMAGE_NAME, ".")
        run("docker", "run", "--rm", "--entrypoint", "python", IMAGE_NAME, "-m", "compileall", "app")
        run(
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            IMAGE_NAME,
            "-m",
            "unittest",
            "discover",
            "-s",
            "app",
            "-p",
            "test_*.py",
            "-v",
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nPREFLIGHT FAILED: {error}", file=sys.stderr)
        return 1

    print("\nPREFLIGHT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
