"""Noise defined on world coordinates, not on the grid."""

import numpy as np

__all__ = ["value_noise", "fbm"]

# Odd constants for the lattice hash, and a SplitMix64 finaliser. Any decent
# integer scramble works; these are the usual ones.
_PRIMES = (73856093, 19349663, 83492791)


def _hash(ix, iy, iz, seed):
    """A repeatable pseudo-random value in [0, 1) for an integer lattice point."""
    h = (ix.astype(np.int64) * _PRIMES[0]) ^ (iy.astype(np.int64) * _PRIMES[1]) ^ (iz.astype(np.int64) * _PRIMES[2])
    h = (h ^ np.int64(seed)).astype(np.uint64)
    h ^= h >> np.uint64(30)
    h = h * np.uint64(0xBF58476D1CE4E5B9)
    h ^= h >> np.uint64(27)
    h = h * np.uint64(0x94D049BB133111EB)
    h ^= h >> np.uint64(31)
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def value_noise(x, y, z, cell_size=10.0, seed=0):
    """Smooth pseudo-random noise in ``[-1, 1]``, from world coordinates.

    The value at a point depends only on where that point is, not on how
    finely the model happens to be sampled. That is the whole reason this
    exists: noise drawn on the grid gives a different rock every time the
    resolution changes, which makes a design unrepeatable. Here, doubling the
    resolution resolves the same noise better instead of replacing it.

    Parameters
    ----------
    x, y, z : float | :class:`numpy.ndarray`
        World coordinates, broadcastable.
    cell_size : float
        Distance between lattice points: the size of the largest blobs.
    seed : int
        Choice of noise. Different seeds give unrelated fields.

    Returns
    -------
    :class:`numpy.ndarray`

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.processes import value_noise
    >>> a = value_noise(np.array([1.0, 2.0]), 0.0, 0.0, cell_size=5.0, seed=1)
    >>> b = value_noise(np.array([1.0, 2.0]), 0.0, 0.0, cell_size=5.0, seed=1)
    >>> bool(np.allclose(a, b)), bool(np.all(np.abs(a) <= 1))
    (True, True)
    """
    shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
    points = [np.broadcast_to(np.asarray(c, dtype=float), shape) / float(cell_size) for c in (x, y, z)]
    floors = [np.floor(p) for p in points]
    fractions = [p - f for p, f in zip(points, floors)]
    # Quintic smoothstep: zero first and second derivatives at the lattice, so
    # the noise has no visible grid direction.
    weights = [f * f * f * (f * (f * 6 - 15) + 10) for f in fractions]
    base = [f.astype(np.int64) for f in floors]

    value = np.zeros(shape)
    for corner in range(8):
        offsets = ((corner >> 0) & 1, (corner >> 1) & 1, (corner >> 2) & 1)
        weight = np.ones(shape)
        for axis, offset in enumerate(offsets):
            weight = weight * (weights[axis] if offset else (1.0 - weights[axis]))
        value += weight * _hash(base[0] + offsets[0], base[1] + offsets[1], base[2] + offsets[2], seed)
    return 2.0 * value - 1.0


def fbm(x, y, z, cell_size=20.0, octaves=4, gain=0.5, lacunarity=2.0, seed=0):
    """Fractal noise: several octaves of :func:`value_noise`, summed.

    Each octave halves the amplitude and halves the feature size, which is
    what gives rock its self-similar look -- the same character at arm's
    length and at building scale.

    Parameters
    ----------
    x, y, z : float | :class:`numpy.ndarray`
        World coordinates, broadcastable.
    cell_size : float
        Feature size of the first, largest octave.
    octaves : int
        How many are summed. Octaves finer than the voxel size are wasted.
    gain : float
        Amplitude factor per octave.
    lacunarity : float
        Frequency factor per octave.
    seed : int

    Returns
    -------
    :class:`numpy.ndarray`
        Values in ``[-1, 1]``.

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.processes import fbm
    >>> field = fbm(*np.ogrid[0:10:8j, 0:10:8j, 0:10:8j], cell_size=6.0, seed=2)
    >>> field.shape, bool(np.all(np.abs(field) <= 1.0))
    ((8, 8, 8), True)
    """
    total = np.zeros(np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z)))
    amplitude, size, weight = 1.0, float(cell_size), 0.0
    for octave in range(int(octaves)):
        total = total + amplitude * value_noise(x, y, z, cell_size=size, seed=seed + 977 * octave)
        weight += amplitude
        amplitude *= gain
        size /= lacunarity
    return total / weight
