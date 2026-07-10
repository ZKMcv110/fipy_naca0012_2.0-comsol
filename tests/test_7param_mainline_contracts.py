from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "七参数_几何掩码代理优化"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_prediction_default_uses_1000_labels_with_1000_model():
    source = read_text(PIPELINE / "10_预测_PI_CNN_CBAM性能.py")

    assert 'ROOT / "ablation_results_1000" / "gp"' in source
    assert 'ROOT / "samples" / "labels_7param_1000.csv"' in source
    assert 'ROOT / "samples" / "labels_7param.csv"' not in source


def test_optimization_default_uses_1000_labels_with_1000_model():
    source = read_text(PIPELINE / "11_差分进化优化_PI_CNN_CBAM七参数.py")

    assert 'ROOT / "ablation_results_1000" / "gp"' in source
    assert 'ROOT / "samples" / "labels_7param_1000.csv"' in source
    assert 'ROOT / "samples" / "labels_7param.csv"' not in source


def test_integrity_check_tracks_theta500_v2_label_rows():
    source = read_text(PIPELINE / "13_七参数项目完整性检查.py")

    assert '"七参数theta500_v2标签": ROOT / "samples" / "labels_7param_theta500_v2.csv"' in source
    assert "theta500_v2_labels" in source
    assert "summary_row_count" in source


def load_integrity_module():
    sys.path.insert(0, str(PIPELINE))
    spec = importlib.util.spec_from_file_location(
        "integrity_check",
        PIPELINE / "13_七参数项目完整性检查.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_integrity_check_builds_dataset_paths_from_dataset_name():
    module = load_integrity_module()

    files = module.build_required_files("1000")

    assert files["七参数标签"] == PIPELINE / "samples" / "labels_7param_1000.csv"
    assert files["七参数数据划分"] == PIPELINE / "samples" / "dataset_split_1000.csv"
    assert files["消融实验汇总"] == PIPELINE / "ablation_results_1000" / "ablation_summary.csv"
    assert files["K折汇总"] == PIPELINE / "kfold_results_1000" / "kfold_summary.json"
    assert files["PI-CNN-CBAM优化参数"] == PIPELINE / "optimization_results_1000_gp" / "best_params.json"
    assert files["COMSOL复核报告"] == PIPELINE / "validation_results_1000_gp" / "final_validation_report.json"


def test_integrity_report_no_longer_warns_about_old_theta0_mainline():
    module = load_integrity_module()

    report = module.build_report(module.build_required_files("1000"))

    assert report["labels"]["sample_count"] == 1000
    assert report["labels"]["theta_nonzero_count"] == 1000
    assert not any("原始训练标签 theta 仍只有0" in warning for warning in report["warnings"])


def test_label_summary_counts_image_complete_rows():
    module = load_integrity_module()

    summary, warnings = module.summarize_labels(
        PIPELINE / "samples" / "labels_7param_theta500_v2.csv"
    )

    assert warnings == []
    assert summary["sample_count"] == 500
    assert summary["image_complete_count"] == 500


def test_kfold_script_uses_current_gp_model_name():
    source = read_text(PIPELINE / "12_七参数PI_CNN_CBAM_K折验证.py")

    assert 'parser.add_argument("--model-name", default="gp"' in source
    assert 'module.run_one_model(args.model_name' in source
    assert '"pi_cnn_cbam"' not in source
