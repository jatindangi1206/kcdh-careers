"""Exercise the backup template without AWS access, root, or production files."""
import json, os, subprocess, sys, tarfile, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    data, code, commands = (root / name for name in ("data", "code", "commands"))
    for path in (data, code / ".venv/bin", commands):
        path.mkdir(parents=True)
    (code / ".venv/bin/python").symlink_to(sys.executable)
    config = root / "backup.env"
    config.write_text("BACKUP_S3_URI=s3://test-bucket/kcdh-careers\nAWS_DEFAULT_REGION=ap-south-1\n")
    source = (Path(__file__).parent / "deploy/aws/backup.sh").read_text()
    for old, new in [("/etc/kcdh-careers-backup.env", str(config)),
                     ("/run/lock/kcdh-careers-maintenance.lock", str(root / "lock")),
                     ("/srv/kcdh-careers", str(code)), ("/var/lib/kcdh-careers", str(data))]:
        source = source.replace(old, new)
    script = root / "backup.sh"
    script.write_text(source)
    for name, body in {
        "git": "echo test-release",
        "flock": "exit 0",
        "systemctl": 'echo "$1" >> "$CALL_LOG"',
        "aws": 'echo upload >> "$CALL_LOG"; [ "${FAIL_UPLOAD:-0}" = 0 ] || exit 17; cp "$3" "$ARCHIVE"',
    }.items():
        path = commands / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o700)
    log, archive = root / "calls", root / "archive.tar.gz"
    env = dict(os.environ, COPYFILE_DISABLE="1", PATH=str(commands) + os.pathsep + os.environ["PATH"],
               CALL_LOG=str(log), ARCHIVE=str(archive))

    for invalid_data, fail_upload in [(False, False), (False, True), (True, False)]:
        log.write_text("")
        archive.unlink(missing_ok=True)
        (data / "internships.json").write_text("broken" if invalid_data else json.dumps([{"id": 123}]))
        (data / "auth.json").write_text(json.dumps({"users": {"staff@example.edu": {"hash": "fixture"}}}))
        result = subprocess.run(["bash", str(script)], env=dict(env, FAIL_UPLOAD=str(int(fail_upload))),
                                capture_output=True, text=True)
        assert (result.returncode != 0) == (invalid_data or fail_upload), result.stderr
        assert log.read_text().splitlines() == (["stop", "start"] if invalid_data else ["stop", "start", "upload"])
        assert archive.exists() == (not invalid_data and not fail_upload)
        if archive.exists():
            with tarfile.open(archive) as backup:
                assert set(backup.getnames()) == {"internships.json", "auth.json", "release.txt"}, backup.getnames()
                assert json.load(backup.extractfile("internships.json")) == [{"id": 123}]
                assert "staff@example.edu" in json.load(backup.extractfile("auth.json"))["users"]
    assert not list(data.glob("*.tar.gz")), "Do not leave backups alongside live data"

print("AWS backup checks ok (simulated services and S3)")
