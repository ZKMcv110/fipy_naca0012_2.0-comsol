# 数据处理脚本说明

这个文件夹集中放置 COMSOL/CNN 主流程中的数据整理、标签重建和完整性检查脚本。

建议从项目根目录运行下面的命令。

## 标签重建

从 `consol_cfddata/case_*_cfd_solution/result.json` 重新生成统一标签文件：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\数据处理\rebuild_labels_from_results.py
```

主要输出：

```text
consol_cfddata/labels.csv
```

## 数据集整理

把 `csv_data/` 中已有的结果表复制/整理为训练用标签文件，并生成摘要：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\数据处理\organize_dataset.py
```

主要输出：

```text
consol_cfddata/labels.csv
consol_cfddata/dataset_summary.txt
```

## 完整性检查

检查每个 case 是否同时具备速度、压力、温度三张图：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\数据处理\check_dataset_integrity.py
```

如果发现缺图，会额外生成：

```text
consol_cfddata/labels_complete.csv
```

## 迁移说明

这些脚本以项目根目录为路径基准，位于 `旧六参数流程/数据处理/` 后仍然读写根目录下的 `consol_cfddata/` 和 `csv_data/`。
