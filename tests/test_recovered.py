from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.data.frozen import full_development_prevalence
from src.recovered.a1_a2a.centering import center_config_precenter
from src.recovered.a1_a2a.nested import build_inner_split
from src.data.dataset import inner_split
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
