"""Reinforcement Learning agent skeleton for strategy diversification.

This file provides a small class with train/evaluate/act interfaces. For the
MVP we keep it as a pluggable interface so different algorithms (stable-baselines3,
torch, etc.) can be integrated later.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class RLAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = None

    def train(self, env, timesteps: int = 10000) -> None:
        """Train the agent in the provided environment (gym-like)."""
        # Placeholder: integrate with stable-baselines3 or a custom trainer
        raise NotImplementedError()

    def load(self, path: str) -> None:
        """Load a trained model from disk."""
        raise NotImplementedError()

    def save(self, path: str) -> None:
        """Save the model to disk."""
        raise NotImplementedError()

    def act(self, observation) -> Dict[str, Any]:
        """Given an observation, return an action dict {symbol, qty, side, price}.

        Must be deterministic for evaluation; stochasticity only used during training.
        """
        raise NotImplementedError()
