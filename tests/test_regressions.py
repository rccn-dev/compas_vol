"""Regression tests for defects carried by the COMPAS 1 version of this package.

Each test here fails against the original code, either because it raised or
because it returned something wrong.
"""

import numpy as np
import pytest
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import QUADRATIC
from compas_vol.combinations import Blend
from compas_vol.combinations import Division
from compas_vol.combinations import Multiplication
from compas_vol.combinations import SmoothUnionList
from compas_vol.microstructures import TPMS
from compas_vol.microstructures import TPMSPolar
from compas_vol.microstructures import Voronoi
from compas_vol.modifications import Blur
from compas_vol.modifications import Sine
from compas_vol.modifications import Twist
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolEllipsoid
from compas_vol.primitives import VolSphere
from compas_vol.primitives import VolTorus


def test_sine_can_be_constructed():
    """Sine.__init__ did ``self.f = f`` with no f in scope -> NameError."""
    s = Sine(VolBox(Box(10, 10, 10)), 0.5)
    assert isinstance(s.get_distance((0, 0, 0)), float)


@pytest.mark.parametrize("cls", [Multiplication, Division])
def test_arithmetic_repr_does_not_raise(cls):
    """Both repr()s referenced a ``self.objs`` attribute they never set."""
    obj = cls(VolSphere(Sphere(5)), VolBox(Box(10, 10, 10)))
    assert cls.__name__ in repr(obj)


def test_blend_rejects_unsupported_ramp():
    """Any t other than 0 or 1 used to silently return None."""
    with pytest.raises(ValueError):
        Blend(VolSphere(Sphere(5)), VolBox(Box(10, 10, 10)), VolSphere(Sphere(3)), 1.0, t=7)


def test_blend_quadratic_returns_a_number_in_the_transition_band():
    a = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    b = VolBox(Box(20, 15, 10), 2.5)
    c = VolSphere(Sphere(3))
    bl = Blend(a, b, c, 10.0, QUADRATIC)
    d = bl.get_distance((3, 0, 0))
    assert d is not None and isinstance(d, float)


def test_ellipsoid_numpy_transform_survives_numpy2():
    """``np.array([x, y, z, 1])`` on ogrid inputs raises on NumPy 2."""
    e = VolEllipsoid(14, 10, 6, frame=Frame((1, 2, 3), (1, 0.3, 0.1), (-0.4, 1, 0.3)))
    x, y, z = np.ogrid[-5:5:5j, -5:5:5j, -5:5:5j]
    assert np.asarray(e.get_distance_numpy(x, y, z)).shape == (5, 5, 5)


def test_torus_numpy_transform_survives_numpy2():
    from compas.geometry import Torus

    t = VolTorus(Torus(7.0, 2.0, frame=Frame((1, 2, 3), (1, 0.3, 0.1), (-0.4, 1, 0.3))))
    x, y, z = np.ogrid[-5:5:5j, -5:5:5j, -5:5:5j]
    assert np.asarray(t.get_distance_numpy(x, y, z)).shape == (5, 5, 5)


def test_twist_honours_its_angle():
    """Both COMPAS 1 methods ignored self.angle entirely."""
    vb = VolBox(Box(20, 15, 10), 1.5)
    straight = Twist(vb, Frame.worldXY(), 0.0)
    twisted = Twist(vb, Frame.worldXY(), 0.15)
    probe = (9.0, 0.0, 6.0)
    assert straight.get_distance(probe) != pytest.approx(twisted.get_distance(probe))


def test_twist_paths_agree():
    """The single-point path rotated by d/10, the numpy path by a fixed 10 rad."""
    vb = VolBox(Box(20, 15, 10), 1.5)
    t = Twist(vb, Frame.worldXY(), 0.1)
    coords = np.linspace(-8, 8, 5)
    x, y, z = np.ogrid[-8:8:5j, -8:8:5j, -8:8:5j]
    vectorized = np.asarray(t.get_distance_numpy(x, y, z))
    single = np.array(
        [[[t.get_distance((a, b, c)) for c in coords] for b in coords] for a in coords]
    )
    np.testing.assert_allclose(vectorized, single, atol=1e-9)


def test_smoothunionlist_numpy_is_not_transposed():
    """The COMPAS 1 version transposed the stack then reduced the wrong axis."""
    spheres = [VolSphere(Sphere(4, point=Point(i * 6, 0, 0))) for i in range(3)]
    u = SmoothUnionList(spheres, 1.0)
    # An asymmetric grid makes a transposed result impossible to miss.
    x, y, z = np.ogrid[-10:10:7j, -5:5:5j, -3:3:3j]
    dm = np.asarray(u.get_distance_numpy(x, y, z))
    assert dm.shape == (7, 5, 3)
    assert dm[0, 0, 0] == pytest.approx(u.get_distance((-10, -5, -3)))


def test_tpms_polar_is_importable_and_callable():
    """TPMSPolar called math.arctan2, which does not exist."""
    t = TPMSPolar("Gyroid", 5.0, 0.1, 6)
    assert isinstance(t.get_distance((3, 4, 0)), float)


def test_tpms_polar_wavelength_property_is_readable():
    """The COMPAS 1 property read an attribute that was never assigned."""
    t = TPMSPolar("Gyroid", 5.0, 0.1, 6)
    assert t.wavelength == 5.0
    assert "TPMSPolar" in repr(t)


def test_tpms_type_by_name_and_index_agree():
    assert TPMS("Gyroid", 5.0).tpmstype == TPMS(0, 5.0).tpmstype
    assert TPMS("schwartzp", 5.0).typename == "SchwartzP"


def test_voronoi_module_imports_without_numpy_core():
    """voronoi.py imported from numpy.core, removed in NumPy 2."""
    import compas_vol.microstructures.voronoi as mod

    assert mod.Voronoi is Voronoi


def test_voronoi_wall_lies_midway_between_two_seeds():
    """The COMPAS 1 field mixed in |c|^2, a term independent of the query point."""
    v = Voronoi([(0, 0, 0), (10, 0, 0)], thickness=1.0)
    # The bisecting plane sits at x = 5.
    assert v.get_distance((5, 0, 0)) == pytest.approx(-0.5)
    assert v.get_distance((5.5, 0, 0)) == pytest.approx(0.0)
    assert v.get_distance((8, 0, 0)) == pytest.approx(2.5)


def test_voronoi_is_translation_equivariant():
    """A field that depended on the distance from the world origin would fail."""
    seeds = [(0, 0, 0), (10, 0, 0), (0, 10, 0)]
    shift = (100, 100, 100)
    a = Voronoi(seeds, 1.0)
    b = Voronoi([tuple(s[i] + shift[i] for i in range(3)) for s in seeds], 1.0)
    probe = (3, 4, 0)
    assert a.get_distance(probe) == pytest.approx(
        b.get_distance(tuple(probe[i] + shift[i] for i in range(3)))
    )


def test_blur_uses_the_current_scipy_namespace():
    """scipy.ndimage.filters was removed in SciPy 1.15."""
    dm = np.random.default_rng(0).random((8, 8, 8))
    assert Blur(dm, 1.0).get_blurred().shape == (8, 8, 8)


def test_platonic_dodecahedron_paths_agree():
    """The numpy branch had a misplaced paren: (1 + sqrt(5)/2) vs (1+sqrt(5))/2."""
    from compas_vol.primitives import PlatonicSolid

    p = PlatonicSolid(10.0, 2)
    coords = np.linspace(-12, 12, 5)
    x, y, z = np.ogrid[-12:12:5j, -12:12:5j, -12:12:5j]
    vectorized = np.asarray(p.get_distance_numpy(x, y, z))
    single = np.array(
        [[[p.get_distance((a, b, c)) for c in coords] for b in coords] for a in coords]
    )
    np.testing.assert_allclose(vectorized, single, atol=1e-9)


def test_heart_single_point_honours_its_frame():
    """The COMPAS 1 single-point method ignored the frame; the numpy one did not."""
    from compas_vol.primitives import Heart

    h = Heart(30, frame=Frame((5, 0, 0), (1, 0, 0), (0, 1, 0)))
    x, y, z = np.ogrid[5:5:1j, 0:0:1j, 0:0:1j]
    assert h.get_distance((5, 0, 0)) == pytest.approx(float(h.get_distance_numpy(x, y, z).ravel()[0]))
