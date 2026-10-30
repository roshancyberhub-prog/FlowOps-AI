import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_setup_separates_secrets_and_refuses_to_replace_files_or_symlinks(tmp_path):
    (tmp_path / "scripts").mkdir()
    script = tmp_path / "scripts/setup-env.py"
    shutil.copy(ROOT / "scripts/setup-env.py", script)
    shutil.copy(ROOT / ".env.example", tmp_path / ".env.example")

    def run(*options):
        return subprocess.run([sys.executable, str(script), *options], capture_output=True)

    assert run().returncode == 0
    assert run("--production-domain", "demo.example.com").returncode == 0
    development = (tmp_path / ".env").read_bytes()
    production = (tmp_path / ".env.production").read_bytes()
    assert b"APP_ENV=production" in production
    assert b"FLOWOPS_ENV_FILE=.env.production" in production
    assert b"replace-with-a-local-password" not in development + production

    def key(data):
        return next(line for line in data.splitlines() if line.startswith(b"WEBHOOK_SIGNING_KEY="))

    assert key(development) != key(production)
    assert stat.S_IMODE((tmp_path / ".env.production").stat().st_mode) == 0o600
    assert run().returncode != 0 and (tmp_path / ".env").read_bytes() == development
    (tmp_path / ".env").unlink()
    (tmp_path / ".env").symlink_to(tmp_path / ".env.production")
    assert run().returncode != 0 and (tmp_path / ".env.production").read_bytes() == production


def test_log_export_reports_percentiles_and_omits_unapproved_fields():
    rows = [
        {
            "message": "request_completed",
            "method": "GET",
            "route": "/leads",
            "status": status,
            "duration_ms": duration,
            "email": "never-export@example.com",
        }
        for status, duration in [(200, 10), (503, 20)]
    ]
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/log-summary.py")],
        input="\n".join(json.dumps(row) for row in rows),
        text=True,
        capture_output=True,
        check=True,
    )
    metrics = json.loads(result.stdout)["routes"][0]
    assert metrics["requests"] == 2 and metrics["server_errors"] == 1
    assert metrics["p50_ms"] == 10 and metrics["p95_ms"] == metrics["p99_ms"] == 20
    assert metrics["duration_histogram_cumulative"]["50"] == 2
    assert "never-export" not in result.stdout
