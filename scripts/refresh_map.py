
import csv
import json
import os
from pathlib import Path


SCHOOLS_CSV = os.environ["SCHOOLS_CSV"]
HEATMAP_CSV = os.environ["HEATMAP_CSV"]

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"No CSV headers found in {path}")
        return list(reader)


def clean(value):
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    # Convert percentages and ordinary numeric fields to numbers.
    numeric = value.replace(",", "")
    if numeric.endswith("%"):
        numeric = numeric[:-1].strip()

    try:
        number = float(numeric)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def write_js(path, variable_name, data):
    content = (
        f"var {variable_name} = "
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    path.write_text(content, encoding="utf-8")


# --- Public school points ---
school_rows = read_csv(SCHOOLS_CSV)
school_features = []

for row in school_rows:
    display_name = (row.get("Display Name") or "").strip()
    full_name = (row.get("Full Name") or "").strip()

    if not display_name and not full_name:
        continue

    raw_coordinates = (row.get("coordinates") or "").strip()
    if not raw_coordinates:
        print(f"WARNING: Skipping school with missing coordinates: {display_name or full_name}")
        continue

    coordinates = json.loads(raw_coordinates)
    if (
        not isinstance(coordinates, list)
        or len(coordinates) != 2
        or not all(isinstance(v, (int, float)) for v in coordinates)
    ):
        raise ValueError(f"Invalid coordinates for school: {display_name or full_name}")

    lon, lat = coordinates
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError(f"Coordinates out of range for school: {display_name or full_name}")

    # Keep the property names the existing map's popups expect.
    props = {
        "SCH_NAME": display_name or full_name,
        "Name": full_name or display_name,
        "Full Name": full_name or None,
        "Community ": clean(row.get("Community")),
    }

    for field in [
        "Neighborhood",
        "School Type",
        "Model Space Summary",
        "Building Age",
        "Enrollment",
        "Capacity",
        "Current Utilization",
        "Utilization (5 year avg)",
        "Building Experience Score (0-4)",
        "Continuum of Services",
        "% Asian",
        "% Black",
        "% Hispanic",
        "% Other",
        "% White",
        "% Multilingual",
        "% SWD",
    ]:
        props[field] = clean(row.get(field))

    school_features.append({
        "type": "Feature",
        "properties": props,
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat],
        },
    })

if not school_features:
    raise ValueError("No valid school features were produced.")

schools_geojson = {
    "type": "FeatureCollection",
    "name": "BPSSchoolLocation_3",
    "crs": {
        "type": "name",
        "properties": {
            "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
        },
    },
    "features": school_features,
}

write_js(
    OUTPUT_DIR / "BPSSchoolLocation_3.js",
    "json_BPSSchoolLocation_3",
    schools_geojson,
)


# --- Aggregated heatmap polygons ---
heatmap_rows = read_csv(HEATMAP_CSV)
heatmap_features = []

for row in heatmap_rows:
    raw_geometry = row.get("geometry")
    if not raw_geometry:
        raise ValueError("A heatmap row is missing geometry.")

    geometry = json.loads(raw_geometry)
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError(
            f"Unexpected heatmap geometry type: {geometry.get('type')}"
        )

    props = {
        key: clean(value)
        for key, value in row.items()
        if key != "geometry"
    }

    heatmap_features.append({
        "type": "Feature",
        "properties": props,
        "geometry": geometry,
    })

if not heatmap_features:
    raise ValueError("No heatmap features were produced.")

heatmap_geojson = {
    "type": "FeatureCollection",
    "name": "BPSEnrollment_2",
    "features": heatmap_features,
}

write_js(
    OUTPUT_DIR / "BPSEnrollment_2.js",
    "json_BPSEnrollment_2",
    heatmap_geojson,
)

print(f"Validated {len(school_features)} public school features.")
print(f"Validated {len(heatmap_features)} aggregate heatmap polygons.")
