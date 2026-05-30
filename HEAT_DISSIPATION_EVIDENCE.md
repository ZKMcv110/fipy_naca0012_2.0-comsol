# Heat Dissipation Evidence Chain

This note records how to replace a simple cloud-map display with a stronger
paper evidence chain:

`cloud maps with contours -> metric bars/table`

## Generated Files

Run:

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\make_heat_dissipation_evidence.py
```

Generated outputs:

| File | Use |
|---|---|
| `paper_figures_svg/Fig9_Heat_Dissipation_Evidence.svg` | Baseline/optimal velocity and temperature cloud maps with contour overlays. |
| `paper_figures_svg/Fig9_Heat_Dissipation_Evidence.png` | PNG version for quick preview or Word import. |
| `paper_figures_svg/Fig9_Heat_Dissipation_Metrics.svg` | Metric bars plus summary table. |
| `paper_figures_svg/Fig9_Heat_Dissipation_Metrics.png` | PNG version for quick preview or Word import. |
| `paper_figures_svg/heat_dissipation_summary.csv` | Numeric source table for the figure and paper table. |

## Current Quantitative Evidence

The current comparison uses `case_1` as the baseline and `case_195` as the
best case selected by `target_param` in `consol_cfddata/labels.csv`.

| Metric | Baseline | Optimal | Change |
|---|---:|---:|---:|
| Nu | 22.999 | 24.847 | +8.04% |
| Q_total | 11077.1 | 11578.3 | +4.53% |
| eta | 66.128 | 70.082 | +5.98% |
| Delta_T_out | 2.655 K | 2.691 K | +1.35% |
| f | 0.04207 | 0.04457 | +5.93% |
| Delta_p | 0.631 Pa | 0.668 Pa | +5.93% |

## Suggested Paper Wording

Compared with the baseline structure, the optimized structure increases Nu by
8.04%, Q_total by 4.53%, and the comprehensive performance index eta by 5.98%.
The friction factor and pressure drop increase by about 5.93%, indicating that
the heat-transfer enhancement is accompanied by a moderate flow-resistance
penalty. Therefore, the optimized structure improves the overall heat
dissipation performance rather than only changing the visual appearance of the
temperature cloud map.

## Important Note About True Profile Curves

The current dataset contains global/average values such as `T_in`, `T_out`,
`Q_total`, `Nu`, `f`, and `delta_p`, but it does not contain real line-profile
data such as `T(y)` at the outlet section. Therefore, the current figure only
adds visual contour overlays to the cloud maps, but does not fabricate a
temperature profile curve from image colors.

For a stronger final paper figure, export line data from COMSOL at the marked
outlet section for both the baseline and optimal cases, then plot the actual
temperature profile. The expected CSV format can be:

```csv
y,T
-0.010,300.12
-0.009,300.35
...
```
