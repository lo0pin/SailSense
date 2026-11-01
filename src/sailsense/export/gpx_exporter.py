import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from sailsense.config import load_config


GPX_NS = "http://www.topografix.com/GPX/1/1"
SS_NS = "https://sailsense.local/gpx/extensions/1"

ET.register_namespace("", GPX_NS)
ET.register_namespace("ss", SS_NS)


def qname(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if value == "" or value.lower() in ("none", "null", "nan"):
        return None

    return value


def add_text(parent, tag: str, value, namespace: str = GPX_NS):
    value = clean(value)

    if value is None:
        return None

    elem = ET.SubElement(parent, qname(namespace, tag))
    elem.text = value
    return elem


def valid_float(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def read_track_rows(track_csv: Path) -> list[dict]:
    with track_csv.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def track_id_from_rows_or_filename(rows: list[dict], track_csv: Path) -> str:
    for row in rows:
        track_id = clean(row.get("track_id"))
        if track_id:
            return track_id

    return track_csv.stem


def export_track_csv_to_gpx(track_csv: str | Path, output_dir: str | Path | None = None) -> Path:
    track_csv = Path(track_csv)

    if not track_csv.exists():
        raise FileNotFoundError(f"Track-CSV nicht gefunden: {track_csv}")

    rows = read_track_rows(track_csv)
    track_id = track_id_from_rows_or_filename(rows, track_csv)

    if output_dir is None:
        output_dir = track_csv.parent

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gpx_path = output_dir / f"{track_id}.gpx"

    root = ET.Element(
        qname(GPX_NS, "gpx"),
        {
            "version": "1.1",
            "creator": "SailSense",
        },
    )

    metadata = ET.SubElement(root, qname(GPX_NS, "metadata"))
    add_text(metadata, "name", track_id)
    add_text(metadata, "time", utc_now_iso())

    trk = ET.SubElement(root, qname(GPX_NS, "trk"))
    add_text(trk, "name", track_id)
    add_text(trk, "desc", "SailSense GPS track export")

    trkseg = ET.SubElement(trk, qname(GPX_NS, "trkseg"))

    exported_points = 0

    for row in rows:
        lat = valid_float(row.get("lat"))
        lon = valid_float(row.get("lon"))

        if lat is None or lon is None:
            continue

        trkpt = ET.SubElement(
            trkseg,
            qname(GPX_NS, "trkpt"),
            {
                "lat": f"{lat:.8f}",
                "lon": f"{lon:.8f}",
            },
        )

        add_text(trkpt, "ele", row.get("alt_m"))
        add_text(trkpt, "time", row.get("timestamp_utc"))

        # GPX-Standardfelder, soweit sinnvoll
        add_text(trkpt, "sat", row.get("sats"))
        add_text(trkpt, "hdop", row.get("hdop"))

        # SailSense-spezifische Erweiterungen.
        # Viele GPX-Viewer ignorieren sie, aber die Daten bleiben sauber erhalten.
        extensions = ET.SubElement(trkpt, qname(GPX_NS, "extensions"))

        extension_values = {
            "speed_kn": row.get("speed_kn"),
            "speed_kmh": row.get("speed_kmh"),
            "course_deg": row.get("course_deg"),
            "fix_quality": row.get("fix_quality"),
            "distance_from_previous_m": row.get("distance_from_previous_m"),
            "distance_total_m": row.get("distance_total_m"),
            "distance_total_nm": row.get("distance_total_nm"),
            "marker": row.get("marker"),
        }

        has_extension = False

        for key, value in extension_values.items():
            if clean(value) is not None:
                add_text(extensions, key, value, namespace=SS_NS)
                has_extension = True

        if not has_extension:
            trkpt.remove(extensions)

        exported_points += 1

    if exported_points == 0:
        raise ValueError(f"Keine gültigen Trackpunkte in {track_csv}")

    ET.indent(root, space="  ", level=0)

    tree = ET.ElementTree(root)
    tree.write(gpx_path, encoding="utf-8", xml_declaration=True)

    return gpx_path


def find_latest_track_csv(track_dir: Path) -> Path:
    candidates = sorted(
        track_dir.glob("track_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(f"Keine Track-CSV gefunden in {track_dir}")

    return candidates[0]


def export_all_tracks(track_dir: Path, output_dir: Path) -> list[Path]:
    result = []

    for track_csv in sorted(track_dir.glob("track_*.csv")):
        result.append(export_track_csv_to_gpx(track_csv, output_dir))

    return result


def main():
    parser = argparse.ArgumentParser(description="SailSense GPX Exporter")
    parser.add_argument(
        "track_csv",
        nargs="?",
        help="Pfad zu einer Track-CSV. Wenn leer, wird --latest verwendet.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Neueste Track-CSV exportieren.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Alle Track-CSV-Dateien exportieren.",
    )

    args = parser.parse_args()

    config = load_config()

    track_config = config["track"]
    export_config = config.get("export", {})

    track_dir = Path(track_config["log_dir"])
    output_dir = Path(export_config.get("gpx_output_dir", "/home/user/sailsense/data/exports"))

    if args.all:
        exported = export_all_tracks(track_dir, output_dir)

        print(f"{len(exported)} GPX-Datei(en) exportiert:")
        for path in exported:
            print(path)

        return

    if args.track_csv:
        track_csv = Path(args.track_csv)
    else:
        track_csv = find_latest_track_csv(track_dir)

    gpx_path = export_track_csv_to_gpx(track_csv, output_dir)

    print("GPX exportiert:")
    print(gpx_path)


if __name__ == "__main__":
    main()
