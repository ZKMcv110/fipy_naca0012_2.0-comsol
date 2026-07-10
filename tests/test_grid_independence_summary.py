from pathlib import Path
import csv
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "七参数_MLP_CNN流场重建" / "15_网格无关性汇总.py"


def load_grid_module():
    spec = importlib.util.spec_from_file_location("grid_independence_summary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "dimension",
        "case",
        "mesh_level",
        "element_count",
        "Nu",
        "f",
        "eta",
        "Tmax",
        "Tavg",
        "pressure_drop",
        "thermal_resistance",
        "relative_to_fine_percent",
        "status",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_assess_grid_rows_marks_2d_medium_fine_passed():
    module = load_grid_module()

    rows = module.assess_grid_rows(
        [
            {"dimension": "2D", "case": "DE_optimum", "mesh_level": "coarse", "Nu": "45.0", "f": "0.110"},
            {"dimension": "2D", "case": "DE_optimum", "mesh_level": "medium", "Nu": "46.0", "f": "0.106"},
            {"dimension": "2D", "case": "DE_optimum", "mesh_level": "fine", "Nu": "46.5", "f": "0.105"},
        ]
    )

    medium = next(row for row in rows if row["mesh_level"] == "medium")
    fine = next(row for row in rows if row["mesh_level"] == "fine")
    assert "medium/fine" in medium["status"]
    assert "medium/fine" in fine["status"]
    assert float(medium["relative_to_fine_percent"]) < 2.0


def test_assess_grid_rows_marks_3d_pressure_drop_failed():
    module = load_grid_module()

    rows = module.assess_grid_rows(
        [
            {"dimension": "3D", "case": "baseline", "mesh_level": "medium", "Tmax": "380.0", "pressure_drop": "0.020"},
            {"dimension": "3D", "case": "baseline", "mesh_level": "fine", "Tmax": "379.5", "pressure_drop": "0.010"},
        ]
    )

    medium = next(row for row in rows if row["mesh_level"] == "medium")
    assert "pressure_drop" in medium["status"]
    assert float(medium["relative_to_fine_percent"]) > 5.0


def test_build_rows_accepts_multiple_input_csvs(tmp_path):
    module = load_grid_module()
    two_d = tmp_path / "two_d.csv"
    three_d = tmp_path / "three_d.csv"
    write_csv(
        two_d,
        [
            {"dimension": "2D", "case": "baseline", "mesh_level": "medium", "Nu": "30.0", "f": "0.090"},
            {"dimension": "2D", "case": "baseline", "mesh_level": "fine", "Nu": "30.3", "f": "0.091"},
        ],
    )
    write_csv(
        three_d,
        [
            {"dimension": "3D", "case": "chip_mlp_cnn_de_multiloss_e10", "mesh_level": "medium", "Tmax": "377.0", "pressure_drop": "0.0130"},
            {"dimension": "3D", "case": "chip_mlp_cnn_de_multiloss_e10", "mesh_level": "fine", "Tmax": "376.8", "pressure_drop": "0.0131"},
        ],
    )

    rows = module.build_rows([two_d, three_d])

    assert any(row["dimension"] == "2D" and row["case"] == "baseline" for row in rows)
    assert any(row["dimension"] == "3D" and row["case"] == "chip_mlp_cnn_de_multiloss_e10" for row in rows)
    assert not any(row.get("case") == "baseline_and_DE_optimum" for row in rows)


def test_assess_grid_rows_uses_last_two_generic_g_levels():
    module = load_grid_module()

    rows = module.assess_grid_rows(
        [
            {"dimension": "2D", "case": "baseline", "mesh_level": "G3", "Nu": "16.0", "f": "0.034"},
            {"dimension": "2D", "case": "baseline", "mesh_level": "G4", "Nu": "13.5", "f": "0.031"},
            {"dimension": "2D", "case": "baseline", "mesh_level": "G5", "Nu": "11.1", "f": "0.027"},
        ]
    )

    g4 = next(row for row in rows if row["mesh_level"] == "G4")
    g5 = next(row for row in rows if row["mesh_level"] == "G5")
    assert "g4/g5" in g4["status"].lower()
    assert "g4/g5" in g5["status"].lower()
    assert float(g4["relative_to_fine_percent"]) > 3.0
