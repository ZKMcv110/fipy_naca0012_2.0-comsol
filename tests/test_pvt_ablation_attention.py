from pathlib import Path
import importlib.util
import sys

import torch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "七参数_MLP_CNN流场重建" / "14_PVT消融实验.py"


def load_ablation_module():
    spec = importlib.util.spec_from_file_location("pvt_ablation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_eca_group_is_available_as_a5():
    module = load_ablation_module()

    config = module.ABLATION_GROUPS["A5"]

    assert config.attention == "eca"
    assert config.use_coords is True
    assert config.use_domain is True
    assert config.use_eta_loss is True
    assert config.use_grad_loss is True
    assert config.predicts_field is True


def test_eca_keeps_feature_shape():
    module = load_ablation_module()
    layer = module.ECA(16)
    x = torch.randn(2, 16, 12, 20)

    y = layer(x)

    assert y.shape == x.shape


def test_default_groups_include_eca_after_cbam():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'parser.add_argument("--groups", default="A0,A1,A2,A3,A4,A5")' in source


def test_collect_metric_rows_keeps_existing_groups_when_one_group_updates(tmp_path):
    module = load_ablation_module()
    for group in ("A0", "A4"):
        group_dir = tmp_path / group
        group_dir.mkdir()
        (group_dir / "metrics.json").write_text(
            f'{{"group": "{group}", "value": "{group}_old"}}',
            encoding="utf-8",
        )

    rows = module.collect_metric_rows(tmp_path, [{"group": "A5", "value": "A5_new"}])

    assert [row["group"] for row in rows] == ["A0", "A4", "A5"]
    assert rows[-1]["value"] == "A5_new"
