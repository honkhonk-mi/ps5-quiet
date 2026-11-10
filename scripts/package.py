"""Build a Decky install ZIP from an explicit runtime-file allowlist."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'package.json').read_text())['version']
FILES = [
    'plugin.json', 'package.json', 'main.py', 'py_modules/gpu_reset.py',
    'dist/index.js', 'dist/index.js.map', 'README.md', 'README.ru.md', 'LICENSE',
    'THIRD_PARTY.md', 'licenses/decky-api-LGPL-2.1.txt', 'licenses/react-icons.txt',
]


def main():
    for name in FILES:
        if not (ROOT / name).is_file():
            raise SystemExit(f'Missing {name}; run npm run build first')
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=True)
    archive = output / f'ps5-quiet-v{VERSION}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for name in FILES:
            # Stable timestamps and permissions; do not copy local filesystem metadata.
            entry = zipfile.ZipInfo(f'ps5-quiet/{name}', (2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(entry, (ROOT / name).read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n')
    print(f'{archive.name}: {checksum}')


if __name__ == '__main__':
    main()
