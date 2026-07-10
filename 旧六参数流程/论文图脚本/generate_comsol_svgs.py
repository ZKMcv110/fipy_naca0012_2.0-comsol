#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unified entry point for COMSOL paper figure generation.

This script keeps the detailed figure builders in their original modules, but
lets the paper figures be regenerated with one command.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Iterator

import generate_cbam_architecture_svg
import generate_paper_svgs
import make_fig8_cfd_comparison
import make_heat_dissipation_evidence


TASKS = ("base", "cbam", "fig8", "heat")


@contextlib.contextmanager
def argv_for(module_name: str, args: list[str]) -> Iterator[None]:
    old_argv = sys.argv[:]
    sys.argv = [module_name, *args]
    try:
        yield
    finally:
        sys.argv = old_argv


def run_base() -> None:
    print("\n[base] generating core paper SVGs")
    generate_paper_svgs.main()


def run_cbam() -> None:
    print("\n[cbam] generating CBAM architecture SVG")
    generate_cbam_architecture_svg.main()


def run_fig8(baseline_case: int, optimal_case: int | None) -> None:
    print("\n[fig8] generating baseline vs optimal CFD field comparison")
    args = ["--baseline-case", str(baseline_case)]
    if optimal_case is not None:
        args.extend(["--optimal-case", str(optimal_case)])
    with argv_for("make_fig8_cfd_comparison.py", args):
        make_fig8_cfd_comparison.main()


def run_heat(baseline_case: int, optimal_case: int | None) -> None:
    print("\n[heat] generating heat-dissipation evidence figures")
    args = ["--baseline-case", str(baseline_case)]
    if optimal_case is not None:
        args.extend(["--optimal-case", str(optimal_case)])
    with argv_for("make_heat_dissipation_evidence.py", args):
        make_heat_dissipation_evidence.main()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate COMSOL/CNN paper SVG figures with one command."
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=TASKS,
        default=list(TASKS),
        help="Figure groups to generate. Default: all.",
    )
    parser.add_argument(
        "--baseline-case",
        type=int,
        default=1,
        help="Baseline case id used by Fig. 8 and heat evidence figures.",
    )
    parser.add_argument(
        "--optimal-case",
        type=int,
        default=None,
        help="Optimal case id used by Fig. 8 and heat evidence figures. Default: max target_param.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = set(args.only)

    if "base" in selected:
        run_base()
    if "cbam" in selected:
        run_cbam()
    if "fig8" in selected:
        run_fig8(args.baseline_case, args.optimal_case)
    if "heat" in selected:
        run_heat(args.baseline_case, args.optimal_case)

    print("\nDone. Outputs are in paper_figures_svg/")


if __name__ == "__main__":
    main()
