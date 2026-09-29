import numpy as np

from adaptiverag.telemetry.trace import Trace
from adaptiverag.types import Classification


def features(question: str) -> np.ndarray:
    """Hand written cue features, documented one per line."""
    raise NotImplementedError


def classify(
    question: str, qvec: np.ndarray, trace: Trace, method: str | None = None
) -> Classification:
    """method: 'rules' | 'logreg' | 'llm'; default from router.toml."""
    raise NotImplementedError
