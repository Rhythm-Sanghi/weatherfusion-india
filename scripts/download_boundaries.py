"""Download the pinned India boundary files and verify their checksums.

The large GeoJSON files are deliberately excluded from Git so a fresh clone
remains small and can be pushed to GitHub without Git LFS.  Their version,
source URL, licence, and expected SHA-256 are tracked in the manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "india_boundaries"
MANIFEST = DATA / "DATASET_MANIFEST.json"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest["datasets"]:
        request = Request(item["url"], headers={"User-Agent": "WeatherFusion-India/1.0"})
        with urlopen(request, timeout=60) as response:  # noqa: S310 - URL is repository-pinned.
            payload = response.read()
        digest = sha256(payload)
        if digest != item["sha256"]:
            raise RuntimeError(
                f"Checksum mismatch for {item['level']}: expected {item['sha256']}, got {digest}"
            )
        target = DATA / item["level"] / f"india_{item['level'].lower()}.geojson"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"Downloaded and verified {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
