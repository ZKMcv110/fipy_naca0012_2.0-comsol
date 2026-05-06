#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rebuild consol_cfddata/labels.csv from each case folder's result.json.

This avoids stale or misaligned CSV files by using the parameters and physics
results saved in the same case directory as the field images.
"""

import argparse
import csv
import json
import math
import os
import re
import shutil
from datetime import datetime


REQUIRED_IMAGES = (
    "velocity_magnitude.png",
    "pressure.png",
    "temperature.png",
)


def parse_case_id(path):
    match = re.search(r"case_(\d+)_cfd_solution$", os.path.basename(path))
    return int(match.group(1)) if match else None


def is_finite_number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def find_case_dirs(data_dir):
    case_dirs = []
    for name in os.listdir(data_dir):
        path = os.path.join(data_dir, name)
        case_id = parse_case_id(path)
        if case_id is not None and os.path.isdir(path):
            case_dirs.append((case_id, path))
    return sorted(case_dirs, key=lambda item: item[0])


def load_case_record(case_id, case_dir, include_incomplete=False):
    result_path = os.path.join(case_dir, "result.json")
    if not os.path.exists(result_path):
        return None, "missing_result_json"

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
    except Exception as exc:
        return None, f"bad_result_json:{exc}"

    params = result.get("case_info", {}).get("parameters", {})
    physics = result.get("physics_results", {})
    derived = result.get("derived_quantities", {})

    missing_images = [
        image_name
        for image_name in REQUIRED_IMAGES
        if not os.path.exists(os.path.join(case_dir, image_name))
    ]
    image_complete = len(missing_images) == 0
    if missing_images and not include_incomplete:
        return None, "missing_images:" + "|".join(missing_images)

    nu = physics.get("Nu")
    f_value = physics.get("f")
    if not is_finite_number(nu) or not is_finite_number(f_value):
        return None, "bad_nu_or_f"

    target_param = nu / (f_value ** (1.0 / 3.0)) if f_value > 0 else float("nan")

    row = {
        "case_id": case_id,
        "Ta": params.get("Ta"),
        "Twa": params.get("Twa"),
        "Tb": params.get("Tb"),
        "Ts": params.get("Ts"),
        "Tt": params.get("Tt"),
        "Tad": params.get("Tad"),
        "Nu": nu,
        "f": f_value,
        "target_param": target_param,
        "T_in": physics.get("T_in"),
        "T_out": physics.get("T_out"),
        "v_in": physics.get("v_in"),
        "v_out": physics.get("v_out"),
        "p_in": physics.get("p_in"),
        "p_out": physics.get("p_out"),
        "T_wing": physics.get("T_wing"),
        "vol": physics.get("vol"),
        "delta_p": derived.get("delta_p"),
        "delta_T": derived.get("delta_T"),
        "Q_total": derived.get("Q_total"),
        "image_complete": image_complete,
        "failure_reason": "",
    }

    missing_params = [
        name for name in ("Ta", "Twa", "Tb", "Ts", "Tt", "Tad")
        if not is_finite_number(row[name])
    ]
    if missing_params:
        return None, "bad_parameters:" + "|".join(missing_params)

    return row, None


def backup_existing_file(path):
    if not os.path.exists(path):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.splitext(path)[0] + f".backup_{timestamp}.csv"
    shutil.copy2(path, backup_path)
    return backup_path


def main():
    parser = argparse.ArgumentParser(description="Rebuild labels.csv from case result.json files.")
    parser.add_argument("--data-dir", default="consol_cfddata",
                        help="Directory containing case_*_cfd_solution folders. Default: consol_cfddata.")
    parser.add_argument("--output", default=None,
                        help="Output CSV path. Default: <data-dir>/labels.csv.")
    parser.add_argument("--num-samples", type=int, default=None,
                        help="Use only the first N valid cases after sorting by case_id.")
    parser.add_argument("--include-incomplete", action="store_true",
                        help="Keep cases with missing field images instead of skipping them.")
    parser.add_argument("--no-backup", action="store_true",
                        help="Do not back up an existing output CSV before overwriting it.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and report counts without writing labels.csv.")
    args = parser.parse_args()

    data_dir = args.data_dir
    output_path = args.output or os.path.join(data_dir, "labels.csv")

    if args.num_samples is not None and args.num_samples <= 0:
        raise ValueError("--num-samples must be a positive integer")
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    rows = []
    skipped = {}
    for case_id, case_dir in find_case_dirs(data_dir):
        row, reason = load_case_record(case_id, case_dir, args.include_incomplete)
        if row is None:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue

        rows.append(row)
        if args.num_samples is not None and len(rows) >= args.num_samples:
            break

    print(f"Valid cases: {len(rows)}")
    if skipped:
        print("Skipped cases:")
        for reason, count in sorted(skipped.items()):
            print(f"  {reason}: {count}")

    if args.dry_run:
        print("Dry run only; labels.csv was not written.")
        return

    if not rows:
        raise RuntimeError("No valid cases found; labels.csv was not written.")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if not args.no_backup:
        backup_path = backup_existing_file(output_path)
        if backup_path:
            print(f"Backed up existing labels to: {backup_path}")

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote labels: {output_path}")


if __name__ == "__main__":
    main()
