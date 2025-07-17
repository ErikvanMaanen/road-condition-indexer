import numpy as np
from main import compute_roughness


def test_compute_roughness_basic():
    sample_rate = 100
    t = np.linspace(0, 1, sample_rate, endpoint=False)
    z = np.sin(2 * np.pi * 2 * t)
    rough = compute_roughness(z.tolist(), 10.0, 1.0)
    assert 0.6 < rough < 0.8


def test_compute_roughness_low_speed():
    sample_rate = 100
    t = np.linspace(0, 1, sample_rate, endpoint=False)
    z = np.sin(2 * np.pi * 2 * t)
    rough = compute_roughness(z.tolist(), 3.0, 1.0)
    assert rough == 0.0
