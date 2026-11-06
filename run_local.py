"""Launch one local service using this interpreter and project configuration."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=['backend', 'frontend'])
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    env = os.environ.copy()
    if args.service == 'backend':
        config = json.loads((root / 'config.json').read_text())
        env['OPENAI_API_KEY'] = config['OPENAI_API_KEY']
        env['OPENAI_API_BASE'] = config['OPENAI_API_BASE']
        command = [sys.executable, '-m', 'gunicorn', '--workers', '1',
                   '--timeout', '120', '--bind', '127.0.0.1:7860', 'app:create_app()']
        cwd = root / 'backend_files'
    else:
        command = [sys.executable, '-m', 'streamlit', 'run',
                   str(root / 'frontend_files/app.py'), '--server.address=127.0.0.1']
        cwd = root
    try:
        return subprocess.call(command, cwd=cwd, env=env)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
