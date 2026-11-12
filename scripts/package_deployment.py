"""Build an allowlisted deployment ZIP without notebook outputs or credentials."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'compose.yaml', '.devcontainer/devcontainer.json', '.devcontainer/Dockerfile', '.env.example',
    'DEPLOYMENT.md', '.gitignore',
    'backend_files/app.py', 'backend_files/rag_utils.py',
    'backend_files/settings.json', 'backend_files/requirements.txt',
    'backend_files/Dockerfile', 'backend_files/.dockerignore',
    'backend_files/faiss_index/index.faiss', 'backend_files/faiss_index/index.pkl',
    'backend_files/faiss_index/manifest.json',
    'frontend_files/app.py', 'frontend_files/requirements.txt',
    'frontend_files/Dockerfile', 'frontend_files/.dockerignore',
]


def main():
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit('Missing deployment files: ' + ', '.join(missing))
    settings = json.loads((ROOT / 'backend_files/settings.json').read_text())
    if set(settings) != {'EMBED_MODEL', 'K', 'FETCH_K', 'MMR_LAMBDA',
                        'MODEL', 'TEMPERATURE', 'TOP_P', 'MAX_TOKENS'}:
        raise SystemExit('Server settings contain unexpected or missing keys.')
    manifest = json.loads((ROOT / 'backend_files/faiss_index/manifest.json').read_text())
    if manifest['embedding_model'] != settings['EMBED_MODEL']:
        raise SystemExit('Index and settings embedding models differ.')
    # Detect accidental inclusion of this project's actual credentials in text files.
    secrets = []
    if (ROOT / 'config.json').exists():
        config = json.loads((ROOT / 'config.json').read_text())
        secrets = [str(config[k]).encode() for k in ['OPENAI_API_KEY']
                   if config.get(k) and len(str(config[k])) >= 8]
    for name in FILES:
        if name.endswith(('.pkl', '.faiss')):
            continue
        content = (ROOT / name).read_bytes()
        if any(secret in content for secret in secrets):
            raise SystemExit('Credential detected in allowlisted file: ' + name)
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    target = out / 'aurora-stays-deployment.zip'
    checksums = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}
    with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, name)
        archive.writestr('deployment-checksums.json', json.dumps(checksums, indent=2))
    print(f'Created {target} ({target.stat().st_size:,} bytes; {len(FILES)} files)')


if __name__ == '__main__':
    main()
