"""Import the pinned G3D boundary manifest atomically into PostGIS."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "india_boundaries"
MANIFEST = json.loads((DATA / "DATASET_MANIFEST.json").read_text())


def main() -> None:
    import os

    engine = create_engine(os.environ.get("DATABASE_URL", "postgresql+psycopg://weatherfusion:weatherfusion@localhost:55432/weatherfusion"))
    with engine.begin() as connection:
        for item in MANIFEST["datasets"]:
            path = DATA / item["level"] / f"india_{item['level'].lower()}.geojson"
            if hashlib.sha256(path.read_bytes()).hexdigest().upper() != item["sha256"]:
                raise RuntimeError(f"Checksum mismatch for {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            features = payload.get("features", [])
            if len(features) != item["features"]:
                raise RuntimeError(f"Feature count mismatch for {path}")
            existing = connection.scalar(text("SELECT id FROM boundary_datasets WHERE boundary_id=:id"), {"id": item["boundary_id"]})
            if existing:
                continue
            dataset_id = uuid4()
            connection.execute(text("""INSERT INTO boundary_datasets (id,boundary_id,administrative_level,source,source_url,license,attribution,version,year_represented,sha256,feature_count,coverage_notes) VALUES (:id,:boundary_id,:level,:source,:url,:license,:attribution,:version,:year,:sha,:count,:notes)"""), {"id":dataset_id,"boundary_id":item["boundary_id"],"level":item["level"],"source":"geoBoundaries gbOpen","url":item["url"],"license":item["license"],"attribution":"geoBoundaries / original source; see LICENSE_AND_ATTRIBUTION.md","version":MANIFEST["release_commit"],"year":item["year"],"sha":item["sha256"],"count":len(features),"notes":"Independent ADM1/ADM2 containment; Lakshadweep cross-vintage mismatch documented."})
            rows=[]
            for feature in features:
                props=feature.get("properties",{}); geometry=feature.get("geometry")
                if not geometry or not props.get("shapeID") or not props.get("shapeName"):
                    raise RuntimeError("Invalid boundary feature")
                rows.append({"id":uuid4(),"dataset":dataset_id,"level":item["level"],"feature":props["shapeID"],"name":props["shapeName"],"code":props.get("shapeISO") or None,"geometry":json.dumps(geometry)})
            connection.execute(text("""INSERT INTO administrative_boundaries (id,dataset_id,administrative_level,source_feature_id,name,source_code,geometry) VALUES (:id,:dataset,:level,:feature,:name,:code,ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry),4326)))"""),rows)
    print("Boundary import complete")


if __name__ == "__main__":
    main()
