from __future__ import annotations

import argparse
from io import BytesIO
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils.config import load_config, repository_path
from src.utils.logging import configure_logging


LOGGER = logging.getLogger(__name__)
PRIMARY = ["C0", "C1", "C2", "C3"]
DISPLAY = {"C0": "12 leads", "C1": "Limb information", "C2": "Precordial information", "C3": "I/II/III"}
COLORS = ["#1f6f8b", "#d1495b", "#edae49", "#6a4c93"]


def save_figure(figure: plt.Figure, output_dir, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ["png", "pdf"]:
        figure.savefig(output_dir / f"{name}.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(figure)


def study_design(output_dir) -> None:
    figure, axis = plt.subplots(figsize=(10.5, 5.5))
    axis.axis("off")
    nodes = [
        (0.10, 0.62, "Labeled clinical TRAIN\n17,016 patients; 17,958 ECGs\nPatient-grouped 5-fold OOF\nEffect estimation + paired CI"),
        (0.40, 0.62, "Frozen C0-C3 models\nPrespecified spatial\ninformation configurations\nHigh-sensitivity operating point"),
        (0.71, 0.62, "Official blind held-out TEST\n1,995 ECGs\nAggregate directional confirmation\nNo adaptive resubmission"),
        (0.40, 0.18, "STAFF III controlled occlusion\n73 patients; paired baseline/occlusion\nPhysiological triangulation\nNot clinical external validation"),
    ]
    for x, y, label in nodes:
        axis.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            transform=axis.transAxes,
            linespacing=1.4,
            bbox={"boxstyle": "round,pad=0.5", "fc": "#f5f7f8", "ec": "#335c67", "lw": 1.4},
        )
    axis.annotate("", xy=(0.31, 0.62), xytext=(0.22, 0.62), xycoords="axes fraction", arrowprops={"arrowstyle": "->", "lw": 1.5})
    axis.annotate("", xy=(0.62, 0.62), xytext=(0.53, 0.62), xycoords="axes fraction", arrowprops={"arrowstyle": "->", "lw": 1.5})
    axis.annotate("", xy=(0.50, 0.30), xytext=(0.50, 0.47), xycoords="axes fraction", arrowprops={"arrowstyle": "->", "lw": 1.5})
    axis.text(0.50, 0.92, "Evidence architecture: cohorts were analyzed separately", ha="center", transform=axis.transAxes, fontsize=13, fontweight="bold")
    save_figure(figure, output_dir, "Figure_1_Study_Design")


def high_sensitivity_tradeoff(performance_path, uncertainty_path, output_dir) -> None:
    performance = pd.read_csv(performance_path)
    uncertainty = pd.read_csv(uncertainty_path)
    data = performance.merge(uncertainty, on="configuration").set_index("configuration").loc[PRIMARY].reset_index()
    positions = np.arange(len(data))
    values = data.specificity_at_tau95.to_numpy()
    low = data.spec95_ci_low.to_numpy()
    high = data.spec95_ci_high.to_numpy()
    figure, axis = plt.subplots(figsize=(8.3, 5.3))
    bars = axis.bar(positions, values, color=COLORS, width=0.64)
    axis.errorbar(positions, values, yerr=np.vstack([values - low, high - values]), fmt="none", color="#202020", capsize=4, lw=1.5)
    axis.set_xticks(positions, [DISPLAY[item] for item in data.configuration])
    axis.set_ylabel("Specificity at approximately 95% sensitivity")
    axis.set_ylim(0, max(0.52, float(high.max()) + 0.06))
    axis.set_title("High-sensitivity specificity in patient-grouped OOF predictions")
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 0.018, f"{value:.3f}", ha="center")
    axis.spines[["top", "right"]].set_visible(False)
    save_figure(figure, output_dir, "Figure_2_High_Sensitivity_Tradeoff")


def blind_confirmation(path, output_dir) -> None:
    data = pd.read_csv(path).set_index("configuration").loc[PRIMARY].reset_index()
    positions = np.arange(len(data))
    width = 0.34
    figure, axis = plt.subplots(figsize=(8.3, 5.3))
    axis.bar(positions - width / 2, data.sensitivity, width, label="Sensitivity", color="#1f6f8b")
    axis.bar(positions + width / 2, data.specificity, width, label="Specificity", color="#d1495b")
    axis.set_xticks(positions, [DISPLAY[item] for item in data.configuration])
    axis.set_ylim(0, 1.04)
    axis.set_ylabel("Aggregate metric")
    axis.set_title("Official blind held-out test confirmation")
    axis.legend(frameon=False, loc="upper right")
    axis.spines[["top", "right"]].set_visible(False)
    save_figure(figure, output_dir, "Figure_3_Blind_Confirmation")


def staffiii_response(path, output_dir, seed: int) -> None:
    data = pd.read_csv(path)
    data = data[data.configuration == "C0"].sort_values("patient_id")
    figure, axis = plt.subplots(figsize=(7.8, 5.5))
    jitter = np.random.default_rng(seed).normal(0, 0.025, len(data))
    axis.scatter(np.zeros(len(data)) + jitter, data.p_baseline, color="#777777", s=18, alpha=0.72)
    axis.scatter(np.ones(len(data)) + jitter, data.p_occlusion, color="#1f6f8b", s=18, alpha=0.72)
    for baseline, occlusion, offset in zip(data.p_baseline, data.p_occlusion, jitter):
        axis.plot([offset, 1 + offset], [baseline, occlusion], color="#9aa7ad", lw=0.5, alpha=0.5)
    axis.set_xticks([0, 1], ["Baseline", "60-70 s during occlusion"])
    axis.set_ylabel("Frozen C0 OMI probability")
    axis.set_title("Within-patient C0 score response to controlled coronary occlusion")
    axis.spines[["top", "right"]].set_visible(False)
    save_figure(figure, output_dir, "Figure_4_STAFFIII_Physiology")


def dry_run() -> None:
    figure, axis = plt.subplots(figsize=(2, 2))
    axis.plot([0, 1], [0, 1])
    buffer = BytesIO()
    figure.savefig(buffer, format="png")
    plt.close(figure)
    if len(buffer.getvalue()) < 100:
        raise RuntimeError("Matplotlib dry-run render failed")
    print("PASS: figure rendering dry run")


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate study figures from local analysis outputs")
    parser.add_argument("--config", default="configs/c0_12lead.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    configure_logging(args.verbose)
    if args.dry_run:
        dry_run()
        return
    config = load_config(args.config)
    output_root = repository_path(config, "outputs")
    figure_dir = output_root / "figures"
    plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans"})
    study_design(figure_dir)
    high_sensitivity_tradeoff(output_root / "evaluation" / "oof_performance.csv", output_root / "evaluation" / "oof_uncertainty.csv", figure_dir)
    blind_path = output_root / "evaluation" / "blind_aggregate.csv"
    if blind_path.exists():
        blind_confirmation(blind_path, figure_dir)
    else:
        LOGGER.warning("Skipping Figure 3: authorized aggregate blind results not found at %s", blind_path.relative_to(config["_repository_root"]))
    staff_path = output_root / "staffiii" / "within_patient_scores.csv"
    if staff_path.exists():
        staffiii_response(staff_path, figure_dir, config["study"]["base_seed"])
    else:
        LOGGER.warning("Skipping Figure 4: local STAFF III scores not found at %s", staff_path.relative_to(config["_repository_root"]))


if __name__ == "__main__":
    main()
