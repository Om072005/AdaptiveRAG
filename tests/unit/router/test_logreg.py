import time
from pathlib import Path

import numpy as np
import pytest

from adaptiverag.router.classify import FEATURES, classify_logreg, logreg_inputs, softmax
from adaptiverag.router.train import CLASSES, fit

DIM = 768 + len(FEATURES)


def blobs(n_per: int = 30) -> tuple[np.ndarray, np.ndarray]:
    """Three separable clouds; the seed makes the test data, the fit itself has no randomness."""
    rng = np.random.default_rng(7)
    centers = np.eye(3, 8) * 4
    x = np.vstack([rng.normal(c, 0.5, size=(n_per, 8)) for c in centers])
    return x, np.repeat(np.arange(3), n_per)


def test_fit_separates_the_classes_and_is_deterministic() -> None:
    x, y = blobs()
    w, b = fit(x, y, lr=0.5, l2=0.001, epochs=200)
    assert (np.argmax(x @ w + b, axis=1) == y).mean() == 1.0
    w2, b2 = fit(x, y, lr=0.5, l2=0.001, epochs=200)
    assert np.array_equal(w, w2) and np.array_equal(b, b2)
    assert w.dtype == np.float32 and w.shape == (8, 3)


def test_softmax_rows_sum_to_one_even_for_large_logits() -> None:
    p = softmax(np.array([[1000.0, 1000.0, 0.0], [0.0, 1.0, 2.0]]))
    assert np.allclose(p.sum(axis=1), 1.0) and np.allclose(p[0], [0.5, 0.5, 0.0])


def test_the_input_row_is_the_embedding_then_the_cues() -> None:
    qvec = np.full(768, 0.5, dtype=np.float32)
    row = logreg_inputs("Who was born first, A or B?", qvec)
    assert row.shape == (DIM,) and np.all(row[:768] == 0.5)


def saved(tmp_path: Path, bias: list[float]) -> Path:
    path = tmp_path / "logreg.npz"
    np.savez(
        path,
        W=np.zeros((DIM, 3), dtype=np.float32),
        b=np.array(bias, dtype=np.float32),
        labels=np.array(CLASSES),
    )
    return path


def test_inference_reads_the_weights_and_keeps_its_own_confidence(tmp_path: Path) -> None:
    path = saved(tmp_path, [0.0, 2.0, 0.0])
    c = classify_logreg("Who founded the company that made X?", np.zeros(768), path)
    assert c.label == "multi_hop" and c.method == "logreg" and c.cost_usd == 0.0
    assert c.confidence == pytest.approx(np.exp(2) / (np.exp(2) + 2))
    assert sum(c.probs.values()) == pytest.approx(1.0)


def test_a_missing_weights_file_says_how_to_make_it(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="adaptiverag.router.train"):
        classify_logreg("q", np.zeros(768), tmp_path / "none.npz")


def test_inference_takes_under_a_millisecond(tmp_path: Path) -> None:
    path = saved(tmp_path, [0.1, 0.2, 0.3])
    qvec = np.random.default_rng(1).normal(size=768).astype(np.float32)
    classify_logreg("warm up", qvec, path)
    started = time.perf_counter()
    for _ in range(200):
        classify_logreg("Which film came out first, Ed Wood or Batman?", qvec, path)
    assert (time.perf_counter() - started) / 200 < 0.001
