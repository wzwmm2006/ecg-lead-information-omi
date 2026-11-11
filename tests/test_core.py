from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.data.preprocessing import downsample_and_normalize
from src.evaluation.threshold import specificity_at_sensitivity
from src.models.cnn import TinyECGCNN
from src.utils.config import load_config


class CoreReproducibilityTests(unittest.TestCase):
    def test_primary_configuration_leads(self) -> None:
        expected = {
            "c0_12lead.yaml": list(range(12)),
            "c1_limb.yaml": list(range(6)),
            "c2_precordial.yaml": list(range(6, 12)),
            "c3_i_ii_iii.yaml": [0, 1, 2],
        }
        for filename, indices in expected.items():
            config = load_config(Path("configs") / filename)
            self.assertEqual(config["configuration"]["lead_indices"], indices)

    def test_frozen_preprocessing_shape_and_scaling(self) -> None:
        signal = np.tile(np.arange(5000, dtype=np.float32), (12, 1))
        output = downsample_and_normalize(signal)
        self.assertEqual(output.shape, (12, 500))
        self.assertEqual(output.dtype, np.float32)
        np.testing.assert_allclose(np.median(output, axis=1), 0.0, atol=1e-6)
        np.testing.assert_allclose(np.std(output, axis=1), 1.0, atol=1e-6)

    def test_threshold_rule(self) -> None:
        labels = np.array([1, 0, 1, 0])
        probabilities = np.array([0.9, 0.8, 0.7, 0.1])
        specificity, threshold, sensitivity = specificity_at_sensitivity(labels, probabilities, target=0.5)
        self.assertEqual(threshold, 0.9)
        self.assertEqual(sensitivity, 0.5)
        self.assertEqual(specificity, 1.0)

    def test_a1_a2a_weights_use_full_development_prevalence(self) -> None:
        from src.data.dataset import patient_training_weights
        from src.data.frozen import full_development_prevalence

        frame = pd.DataFrame(
            {
                "patient_id": ["p1", "p1", "p2", "p3"],
                "omi": [1, 1, 0, 0],
            }
        )
        weights = patient_training_weights(frame)
        expected_omi = 0.5 * (1.0 / full_development_prevalence)
        expected_non_omi = 1.0 * (1.0 / (1.0 - full_development_prevalence))
        self.assertAlmostEqual(weights[0], expected_omi)
        self.assertAlmostEqual(weights[2], expected_non_omi)

    def test_wfdb_validation_rejects_wrong_lead_order(self) -> None:
        record = type(
            "Record",
            (),
            {
                "fs": 500,
                "sig_len": 5000,
                "sig_name": ["II", "I", "III", "AVR", "AVL", "AVF", "V1", "V2", "V3", "V4", "V5", "V6"],
                "units": ["mV"] * 12,
                "d_signal": 0,
                "p_signal": np.zeros((5000, 12), dtype=np.float32),
            },
        )()
        from src.data.preprocessing import validate_wfdb_record

        with self.assertRaises(ValueError):
            validate_wfdb_record(record, "test")

    def test_model_output_shape(self) -> None:
        model = TinyECGCNN(3).eval()
        with torch.no_grad():
            output = model(torch.zeros(2, 3, 500))
        self.assertEqual(tuple(output.shape), (2,))


if __name__ == "__main__":
    unittest.main()
