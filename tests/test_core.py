from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
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

    def test_model_output_shape(self) -> None:
        model = TinyECGCNN(3).eval()
        with torch.no_grad():
            output = model(torch.zeros(2, 3, 500))
        self.assertEqual(tuple(output.shape), (2,))


if __name__ == "__main__":
    unittest.main()
