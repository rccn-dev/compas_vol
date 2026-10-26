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
    assert TPMS("schwarzp", 5.0).typename == "SchwarzP"


def test_tpms_old_schwartz_spelling_still_resolves():
    """The type was misspelled "SchwartzP"; scripts using it keep working."""
    assert TPMS("SchwartzP", 5.0).tpmstype == TPMS("SchwarzP", 5.0).tpmstype == 1


@pytest.mark.parametrize("bad", ["Gyroyd", "Schwarz", 7, -1])
def test_tpms_unknown_type_raises(bad):
    """An unknown name used to fall back to the gyroid without a word."""
    with pytest.raises(ValueError):
        TPMS(bad, 5.0)


@pytest.mark.parametrize("tpmstype", ["Gyroid", "SchwarzP", "Diamond", "Neovius", "Lidinoid", "FischerKoch", "IWP"])
def test_tpms_formulas_have_cyclic_symmetry(tpmstype):
    """Every surface here is invariant under x -> y -> z -> x.

    Upstream's Neovius read ``3 cos x + cos y + cos z`` instead of
    ``3 (cos x + cos y + cos z)``, and its Lidinoid had two index typos. Both
    broke this symmetry, so they were not the surfaces they were named after.
    """
    rng = np.random.default_rng(0)
    x, y, z = rng.uniform(-10, 10, (3, 500))
    t = TPMS(tpmstype, np.pi)  # wavelength pi -> unscaled coordinates
    np.testing.assert_allclose(t.get_distance_numpy(x, y, z), t.get_distance_numpy(y, z, x), atol=1e-12)


def test_neovius_matches_reference_formula():
    t = TPMS("Neovius", np.pi)
    x, y, z = 0.3, 1.1, -0.7
    expected = 3 * (np.cos(x) + np.cos(y) + np.cos(z)) + 4 * np.cos(x) * np.cos(y) * np.cos(z)
    assert t.get_distance((x, y, z)) == pytest.approx(expected)


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


def test_shell_node_centres_the_wall_on_the_surface():
    """The Shell component promised a centred wall but built Shell's default.

    ``Shell(side=0)`` offsets the whole wall outward, so a 2 mm shell of a
    10 mm sphere ran from r=5 to r=7 instead of 4 to 6.
    """
    from compas_vol import nodes

    wall = nodes.shell(nodes.sphere(None, 5.0), 2.0)
    assert wall.get_distance([5, 0, 0]) == pytest.approx(-1.0)
    assert wall.get_distance([4, 0, 0]) == pytest.approx(0.0)
    assert wall.get_distance([6, 0, 0]) == pytest.approx(0.0)


# ==============================================================================
# Defects found in this fork
# ==============================================================================


def test_piece_export_is_closed_at_its_cut_faces(tmp_path):
    """A piece fills its box to the cut, so sampling exactly the box left the cut open."""
    pytest.importorskip("skimage", reason="needs the meshing extra")
    import struct

    from compas_vol.assembly import segment

    assembly = segment(VolBox(Box(300.0, 100.0, 100.0), 0.0), bounds=(-160, -60, -60, 160, 60, 60),
                       piece=(110.0, 200.0, 200.0))
    path = assembly[1].export_stl(str(tmp_path / "piece.stl"), resolution=40)
    with open(path, "rb") as f:
        f.read(80)
        count = struct.unpack("<I", f.read(4))[0]
        data = np.frombuffer(f.read(count * 50), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    _, index = np.unique(data["v"].reshape(-1, 3), axis=0, return_inverse=True)
    corners = index.reshape(-1, 3)
    edges = np.sort(np.concatenate([corners[:, [0, 1]], corners[:, [1, 2]], corners[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert (counts == 2).all()


def test_iso_surface_has_no_degenerate_triangles_on_a_grid_plane():
    """A face exactly on a grid plane used to give zero-area triangles."""
    pytest.importorskip("skimage", reason="needs the meshing extra")
    from compas_vol.meshing import iso_surface

    x, y, z = np.ogrid[-4:4:9j, -4:4:9j, -4:4:9j]
    slab = np.maximum(np.abs(z) - 2.0, np.maximum(np.abs(x), np.abs(y)) - 3.0)   # faces on z = +-2, samples there
    vertices, faces = iso_surface(np.broadcast_to(slab, (9, 9, 9)), (-4, -4, -4), (1, 1, 1))
    area = np.linalg.norm(np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                                   vertices[faces[:, 2]] - vertices[faces[:, 0]]), axis=1)
    assert area.min() > 1e-6


def test_pitting_resistance_means_resistance():
    """1 resisted in differential and pitted fastest in pitting; now both resist."""
    pytest.importorskip("skfmm", reason="needs the processes extra")
    from compas_vol.processes import Field, pitting

    field = Field.from_object(VolSphere(Sphere(10, point=Point(0, 0, 0))), bounds=15.0, resolution=31)
    resistant = pitting(field, resistance=np.ones(field.shape), depth=3.0, steps=4)
    weak = pitting(field, resistance=-np.ones(field.shape), depth=3.0, steps=4)
    assert resistant.solid_fraction() == pytest.approx(field.solid_fraction(), abs=1e-3)
    assert weak.solid_fraction() < field.solid_fraction() - 0.01


def test_transformed_coordinates_do_not_broadcast_over_axes_they_ignore():
    """An axis-aligned frame left a plan shape evaluated once per voxel instead of once per plan point."""
    from compas_vol.base import transform_numpy

    x, y, z = np.ogrid[0:1:5j, 0:1:6j, 0:1:7j]
    identity = [[1, 0, 0, 2], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    xt, yt, zt = transform_numpy(identity, x, y, z)
    assert (xt.shape, yt.shape, zt.shape) == ((5, 1, 1), (1, 6, 1), (1, 1, 7))
    assert np.allclose(xt, x + 2)
