import os
import subprocess
import sys


def test_the_api_does_not_load_yt_dlp() -> None:
    # A fresh interpreter: this test run has loaded yt-dlp already. It gets
    # this run's import path, which pytest sets up without PYTHONPATH.
    code = (
        "import sys\n"
        "from localreel.entrypoints.api.main import create_app\n"
        "create_app()\n"
        "assert 'yt_dlp' not in sys.modules\n"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env)

    assert result.returncode == 0, result.stderr.decode()
