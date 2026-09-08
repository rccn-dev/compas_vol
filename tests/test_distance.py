"""The two distance implementations of every object must agree."""

import numpy as np
import pytest
from compas.geometry import Point

GRID = 7
EXTENT = 15.0


def _grid():
    coords = np.linspace(-EXTENT, EXTENT, GRID)
    x, y, z = np.ogrid[
        -EXTENT : EXTENT : GRID * 1j, -EXTENT : EXTENT : GRID * 1j, -EXTENT : EXTENT : GRID * 1j
    ]
    return coords, x, y, z


def test_numpy_matches_single_point(volobject):
    """get_distance_numpy must reproduce get_distance on the same grid.

    This is the check that catches the axis-ordering and broadcasting bugs the
    COMPAS 1 code had, where the vectorized path silently returned a
    transposed or wrongly-shaped field.
    """
    coords, x, y, z = _grid()

    vectorized = np.asarray(volobject.get_distance_numpy(x, y, z), dtype=float)
    assert vectorized.shape == (GRID, GRID, GRID)

    single = np.array(
        [[[volobject.get_distance((a, b, c)) for c in coords] for b in coords] for a in coords]
    )

    np.testing.assert_allclose(vectorized, single, rtol=1e-9, atol=1e-9)


def test_get_distance_does_not_mutate_input(volobject):
    """Querying a Point must not transform it in place.

    Objects that work in a local frame used to call ``point.transform(...)`` on
    the caller's own Point, so a second query with the same Point returned a
    different answer.
    """
    p = Point(3.0, 4.0, 5.0)
    first = volobject.get_distance(p)
    second = volobject.get_distance(p)

    assert list(p) == [3.0, 4.0, 5.0]
    assert first == pytest.approx(second)


def test_accepts_tuple_and_point_alike(volobject):
    """A bare tuple and a Point must give the same distance."""
    assert volobject.get_distance((1.5, -2.5, 3.5)) == pytest.approx(
        volobject.get_distance(Point(1.5, -2.5, 3.5))
    )


def test_repr_is_not_broken(volobject):
    """repr() must not raise.

    Division and Multiplication used to reference a ``self.objs`` attribute
    they never defined.
    """
    assert isinstance(repr(volobject), str)
    assert repr(volobject)
