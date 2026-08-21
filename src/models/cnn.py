from __future__ import annotations

import torch
from torch import nn


class TinyECGCNN(nn.Module):
    """Frozen lightweight raw-waveform CNN used for all lead configurations."""

    def __init__(self, input_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(input_channels, 32, 11, padding=5),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(4),
            nn.Conv1d(32, 64, 9, padding=4),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(4),
            nn.Conv1d(64, 96, 7, padding=3),
            nn.BatchNorm1d(96),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.fc = nn.Linear(96, 1)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.fc(self.net(inputs).squeeze(-1)).squeeze(-1)
