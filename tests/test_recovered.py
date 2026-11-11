from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.data.frozen import full_development_prevalence
from src.recovered.a1_a2a.centering import center_config_precenter
from src.recovered.a1_a2a.nested import build_inner_split
from src.data.dataset import inner_split
from src.recovered.p3.bootstrap import _sample_patient_rows, paired_tpr95_bootstrap
from src.recovered.p3.matched_tpr import specificity_at_tpr
from src.recovered.sampling.rate_preprocessing import block_mean_500hz, reduce_window_milliseconds


class RecoveredAnalysisTests(unittest.TestCase):
    def test_full_development_weighting(self) -> None:
        self.assertAlmostEqual(full_development_prevalence, 1151 / 17958, places=15)

    def test_a2a_configuration_local_centering(self) -> None:
        values = np.zeros((4, 12, 5), dtype=np.float32)
        values[:, 3, :] = 2.0
        values[:, 0, :] = 10.0
        values[:, 1, :] = 20.0
        values[0, 0, 0] = np.nan
        centered = center_config_precenter(values, [0, 1])
        self.assertEqual(centered["z"].shape, (4, 2, 5))
        self.assertTrue(np.isfinite(centered["z"]).all())
        self.assertAlmostEqual(centered["center_mv"], 15.0)

    def test_inner_split_is_patient_disjoint(self) -> None:
        fold = pd.DataFrame({"patient_id": [f"p{i:03d}" for i in range(20)], "fold": [i % 5 for i in range(20)]})
        labels = pd.DataFrame({"patient_id": [f"p{i:03d}" for i in range(20)], "omi": (np.arange(20) % 4 == 0).astype(int)})
        split = build_inner_split(fold, labels, outer_fold=0)
        self.assertFalse(set(split.loc[split.inner_role == "INNER_MODEL_FIT", "patient_id"]) & set(split.loc[split.inner_role == "INNER_THRESHOLD_CALIBRATION", "patient_id"]))
        self.assertFalse(set(split.patient_id) & set(fold.loc[fold.fold == 0, "patient_id"]))

    def test_public_inner_split_excludes_outer_patients(self) -> None:
        frame = pd.DataFrame(
            {
                "patient_id": [f"p{i:03d}" for i in range(40) for _ in range(2)],
                "omi": [int(i % 4 == 0) for i in range(40) for _ in range(2)],
                "fold": [i % 5 for i in range(40) for _ in range(2)],
            }
        )
        roles = inner_split(frame, outer_fold=0)
        outer = set(roles.loc[roles.inner_role == "OUTER_EVALUATION", "patient_id"])
        inner = set(roles.loc[roles.inner_role != "OUTER_EVALUATION", "patient_id"])
        self.assertFalse(outer & inner)
        self.assertEqual(len(roles), 40)
        self.assertEqual(roles.groupby("patient_id").inner_role.nunique().max(), 1)
        cal = set(roles.loc[roles.inner_role == "INNER_THRESHOLD_CALIBRATION", "patient_id"])
        fit = set(roles.loc[roles.inner_role == "INNER_MODEL_FIT", "patient_id"])
        self.assertFalse(cal & fit)

    def test_matched_tpr_interpolation(self) -> None:
        labels = np.array([0, 0, 0, 1, 1, 1, 1])
        probabilities = np.array([0.95, 0.05, 0.10, 0.90, 0.80, 0.70, 0.60])
        result = specificity_at_tpr(labels, probabilities, 0.85)
        self.assertGreater(result["specificity_at_tpr"], 0.0)
        self.assertLessEqual(result["specificity_at_tpr"], 1.0)
        self.assertTrue(np.isfinite(result["det_threshold"]))

    def test_p3_bootstrap_replicates_vary_and_preserve_patient_multiplicity(self) -> None:
        generator = np.random.default_rng(3)
        rows = []
        for fold in range(2):
            for patient_index in range(24):
                patient_id = f"p{fold}{patient_index:02d}"
                label = int(patient_index < 6)
                for config, offset in (("C0", 0.0), ("C1", -0.10)):
                    probability = min(0.99, max(0.01, float(generator.uniform()) + offset))
                    rows.append({"patient_id": patient_id, "outer_fold": fold, "configuration": config, "omi_label": label, "probability": probability})
        frame = pd.DataFrame(rows)
        folds = [frame[frame.outer_fold == fold] for fold in sorted(frame.outer_fold.unique())]
        patients = np.array(sorted(folds[0].patient_id.unique()), dtype=object)
        chosen = np.repeat(patients[:3], [3, 2, 1])
        sampled = _sample_patient_rows(folds[0], chosen)
        self.assertEqual(len(sampled), sum(len(folds[0][folds[0].patient_id == patient]) * count for patient, count in zip(patients[:3], [3, 2, 1])))
        summary, raw, fold_weights = paired_tpr95_bootstrap(frame, replicate_count=30, seed=17)
        valid = raw[raw.valid]
        self.assertEqual(len(valid), 30)
        self.assertGreater(valid.delta_specificity.nunique(), 1)
        self.assertGreaterEqual(summary[0]["valid_replicates"], 2)
        self.assertEqual(fold_weights, {0: 36, 1: 36})
        self.assertGreater(summary[0]["ci_high"], summary[0]["ci_low"])

    def test_p3_bootstrap_keeps_multiple_ecgs_per_patient(self) -> None:
        rows = []
        for fold in range(2):
            for patient_index in range(20):
                patient_id = f"p{fold}{patient_index:02d}"
                label = int(patient_index < 5)
                for ecg_index in range(1 + patient_index % 3):
                    for config, offset in (("C0", 0.0), ("C1", -0.10)):
                        probability = min(0.99, max(0.01, 0.20 + 0.03 * patient_index + 0.15 * label + offset + 0.01 * ecg_index))
                        rows.append({"patient_id": patient_id, "outer_fold": fold, "configuration": config, "omi_label": label, "probability": probability, "ecg_id": f"{patient_id}-{ecg_index}"})
        frame = pd.DataFrame(rows)
        _, raw, _ = paired_tpr95_bootstrap(frame, replicate_count=20, seed=19)
        _, reference, _ = paired_tpr95_bootstrap(frame, replicate_count=20, seed=19)
        self.assertTrue(raw.equals(reference))
        fold_zero = frame[frame.outer_fold == 0]
        patients = np.array(sorted(fold_zero.patient_id.unique()), dtype=object)
        chosen = np.repeat(patients[:2], [4, 1])
        sampled = _sample_patient_rows(fold_zero, chosen)
        self.assertEqual(len(sampled), sum(len(fold_zero[fold_zero.patient_id == patient]) * count for patient, count in zip(patients[:2], [4, 1])))
        self.assertEqual(sampled.ecg_id.nunique(), len(fold_zero[(fold_zero.patient_id.isin(patients[:2])) & (fold_zero.configuration == "C0")]))

    def test_p3_bootstrap_all_invalid_replicates_are_reported(self) -> None:
        rows = []
        for fold in range(2):
            for patient_index in range(8):
                for config in ("C0", "C1"):
                    rows.append({
                        "patient_id": f"p{fold}{patient_index}",
                        "outer_fold": fold,
                        "configuration": config,
                        "omi_label": 1,
                        "probability": 0.5 + 0.01 * patient_index,
                    })
        summary, raw, weights = paired_tpr95_bootstrap(pd.DataFrame(rows), replicate_count=3, seed=4)
        self.assertEqual(len(raw), 1)
        self.assertFalse(raw.valid.iloc[0])
        self.assertEqual(summary[0]["valid_replicates"], 0)
        self.assertTrue(np.isnan(summary[0]["ci_low"]))
        self.assertEqual(weights, {0: 0, 1: 0})

    def test_sampling_window_is_milliseconds(self) -> None:
        self.assertEqual(reduce_window_milliseconds(output_samples=500, block_native_samples=10)["output_sampling_rate_hz"], 50.0)
        self.assertEqual(reduce_window_milliseconds(output_samples=1000, block_native_samples=5)["output_sampling_rate_hz"], 100.0)
        self.assertEqual(reduce_window_milliseconds(output_samples=2500, block_native_samples=2)["output_sampling_rate_hz"], 250.0)
        self.assertEqual(reduce_window_milliseconds(output_samples=500, block_native_samples=10)["block_duration_ms"], 20.0)
        self.assertEqual(reduce_window_milliseconds(output_samples=1000, block_native_samples=5)["block_duration_ms"], 10.0)
        self.assertEqual(reduce_window_milliseconds(output_samples=2500, block_native_samples=2)["block_duration_ms"], 4.0)
        signal = np.zeros((12, 5000), dtype=np.float32)
        self.assertEqual(block_mean_500hz(signal, 500).shape, (12, 500))


if __name__ == "__main__":
    unittest.main()
