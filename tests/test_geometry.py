"""Analytic checks, so the distance fields are right and not merely consistent."""

import math

import numpy as np
import pytest
from compas.geometry import Box
from compas.geometry import Cone
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere
from compas.geometry import Torus

from compas_vol.combinations import Intersection
from compas_vol.combinations import Subtraction
from compas_vol.combinations import Union
from compas_vol.microstructures import TPMSSolid
from compas_vol.microstructures import Voronoi
from compas_vol.modifications import Offset
from compas_vol.modifications import Remap
from compas_vol.modifications import Shell
from compas_vol.modifications import VolTransformation
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolCapsule
from compas_vol.primitives import VolCone
from compas_vol.primitives import VolCylinder
from compas_vol.primitives import VolPlane
from compas_vol.primitives import VolSphere
from compas_vol.primitives import VolTorus


class TestSphere:
    def test_centre_distance_is_minus_radius(self):
        vs = VolSphere(Sphere(5, point=Point(1, 2, 3)))
        assert vs.get_distance((1, 2, 3)) == pytest.approx(-5.0)

    def test_surface_is_zero(self):
        vs = VolSphere(Sphere(5, point=Point(1, 2, 3)))
        assert vs.get_distance((6, 2, 3)) == pytest.approx(0.0)

    def test_outside_is_euclidean(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        assert vs.get_distance((10, 0, 0)) == pytest.approx(5.0)

    def test_center_property_survives_compas2_rename(self):
        """COMPAS 2 removed Sphere.center in favour of Sphere.base."""
        vs = VolSphere(Sphere(5, point=Point(1, 2, 3)))
        assert list(vs.center) == [1.0, 2.0, 3.0]


class TestBox:
    def test_centre_distance_is_half_smallest_side(self):
        vb = VolBox(Box(20, 15, 10))
        assert vb.get_distance((0, 0, 0)) == pytest.approx(-5.0)

    def test_face_is_zero(self):
        vb = VolBox(Box(20, 15, 10))
        assert vb.get_distance((10, 0, 0)) == pytest.approx(0.0)

    def test_corner_distance_is_euclidean(self):
        vb = VolBox(Box(2, 2, 2))
        # (2,2,2) is offset (1,1,1) from the corner at (1,1,1)
        assert vb.get_distance((2, 2, 2)) == pytest.approx(math.sqrt(3))

    def test_fillet_rounds_the_corner(self):
        vb = VolBox(Box(2, 2, 2), 0.5)
        assert vb.get_distance((2, 2, 2)) == pytest.approx(math.sqrt(3 * 1.5**2) - 0.5)

    def test_volume_without_fillet(self):
        assert VolBox(Box(2, 3, 4)).volume == pytest.approx(24.0)

    def test_negative_radius_is_clamped(self):
        assert VolBox(Box(2, 2, 2), -3).radius == 0.0

    def test_rejects_non_box(self):
        with pytest.raises(TypeError):
            VolBox(Sphere(1))


class TestCylinderConeTorus:
    def test_cylinder_centre(self):
        vc = VolCylinder(Cylinder(5, 8))
        assert vc.get_distance((0, 0, 0)) == pytest.approx(-4.0)

    def test_cylinder_side_is_zero(self):
        vc = VolCylinder(Cylinder(5, 8))
        assert vc.get_distance((5, 0, 0)) == pytest.approx(0.0)

    def test_torus_tube_centre(self):
        vt = VolTorus(Torus(7.0, 2.0))
        assert vt.get_distance((7, 0, 0)) == pytest.approx(-2.0)

    def test_torus_surface_is_zero(self):
        vt = VolTorus(Torus(7.0, 2.0))
        assert vt.get_distance((9, 0, 0)) == pytest.approx(0.0)

    def test_cone_uses_frame_not_removed_plane(self):
        """COMPAS 2 removed Cone.plane; VolCone must work off the frame."""
        vc = VolCone(Cone(5, 8, frame=Frame((1, 2, 3), (1, 0, 0), (0, 1, 0))))
        assert vc.get_distance((1, 2, 3)) == pytest.approx(-2.5)


class TestPlaneAndCapsule:
    def test_plane_signed_distance(self):
        vp = VolPlane(Plane((0, 0, 0), (0, 0, 1)))
        assert vp.get_distance((3, 4, 5)) == pytest.approx(5.0)
        assert vp.get_distance((3, 4, -5)) == pytest.approx(-5.0)

    def test_capsule_endpoint(self):
        c = VolCapsule(((0, 0, 0), (10, 0, 0)), 3.0)
        assert c.get_distance((0, 0, 0)) == pytest.approx(-3.0)

    def test_capsule_beyond_the_end_is_spherical(self):
        c = VolCapsule(((0, 0, 0), (10, 0, 0)), 3.0)
        assert c.get_distance((14, 0, 0)) == pytest.approx(1.0)

    def test_capsule_broadside(self):
        c = VolCapsule(((0, 0, 0), (10, 0, 0)), 3.0)
        assert c.get_distance((5, 8, 0)) == pytest.approx(5.0)


class TestBooleans:
    def setup_method(self):
        self.a = VolSphere(Sphere(5, point=Point(-2, 0, 0)))
        self.b = VolSphere(Sphere(5, point=Point(2, 0, 0)))

    def test_union_takes_the_minimum(self):
        u = Union(self.a, self.b)
        assert u.get_distance((-2, 0, 0)) == pytest.approx(-5.0)

    def test_intersection_takes_the_maximum(self):
        i = Intersection(self.a, self.b)
        assert i.get_distance((0, 0, 0)) == pytest.approx(-3.0)

    def test_subtraction_negates_the_second(self):
        s = Subtraction(self.a, self.b)
        # Inside a and clear of b: the distance to a's surface wins.
        assert s.get_distance((-5, 0, 0)) == pytest.approx(-2.0)

    def test_subtraction_carves_away_the_overlap(self):
        s = Subtraction(self.a, self.b)
        # Deep inside a, but also inside b, so the result is outside the solid.
        assert s.get_distance((-2, 0, 0)) == pytest.approx(1.0)

    def test_union_of_a_list(self):
        u = Union([self.a, self.b, VolSphere(Sphere(1, point=Point(20, 0, 0)))])
        assert len(u.objs) == 3
        assert u.get_distance((20, 0, 0)) == pytest.approx(-1.0)

    def test_add_object_extends_the_union(self):
        u = Union(self.a, self.b)
        u.add_object(VolSphere(Sphere(1, point=Point(20, 0, 0))))
        assert u.get_distance((20, 0, 0)) == pytest.approx(-1.0)


class TestShell:
    def test_shell_is_hollow_at_the_centre(self):
        vs = VolSphere(Sphere(10, point=Point(0, 0, 0)))
        sh = Shell(vs, 2.0, 0.5)
        assert sh.get_distance((0, 0, 0)) > 0

    def test_shell_is_solid_on_the_surface(self):
        vs = VolSphere(Sphere(10, point=Point(0, 0, 0)))
        sh = Shell(vs, 2.0, 0.5)
        assert sh.get_distance((10, 0, 0)) == pytest.approx(-1.0)


class TestTransformation:
    def test_moves_the_object(self):
        vb = VolBox(Box(10, 10, 10))
        t = VolTransformation(vb, Frame((20, 0, 0), (1, 0, 0), (0, 1, 0)))
        assert t.get_distance((20, 0, 0)) == pytest.approx(-5.0)
        assert t.get_distance((0, 0, 0)) == pytest.approx(15.0)


class TestGradient:
    def test_points_outward_on_the_surface(self, gradient):
        v = gradient.get_gradient(Point(5, 0, 0))
        assert (v.x, v.y, v.z) == pytest.approx((1.0, 0.0, 0.0), abs=1e-6)

    def test_tetrahedron_and_regular_methods_agree(self, gradient):
        # Two different finite-difference stencils, so they agree only to the
        # order of the step size rather than exactly.
        a = gradient.get_gradient(Point(3, 4, 1))
        b = gradient.get_gradient_regular(Point(3, 4, 1))
        assert (a.x, a.y, a.z) == pytest.approx((b.x, b.y, b.z), abs=1e-2)

    def test_numpy_returns_a_unit_vector_field(self, gradient):
        x, y, z = np.ogrid[2:8:5j, 2:8:5j, 2:8:5j]
        g = gradient.get_gradient_numpy(x, y, z)
        assert g.shape == (5, 5, 5, 3)
        np.testing.assert_allclose(np.linalg.norm(g, axis=-1), 1.0, atol=1e-6)


class TestCurvature:
    def test_sphere_mean_curvature_is_one_over_radius(self, curvature):
        assert curvature.get_curvature(Point(5, 0, 0)) == pytest.approx(0.2, abs=1e-3)

    def test_numpy_shape(self, curvature):
        x, y, z = np.ogrid[2:8:5j, 2:8:5j, 2:8:5j]
        assert curvature.get_curvature_numpy(x, y, z).shape == (5, 5, 5)


class TestTPMSSolid:
    @staticmethod
    def _wall_thickness(solid, point, normal):
        """Measure the solid run through ``point`` along ``normal``."""
        normal = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
        s = np.linspace(-solid.cell_size / 4, solid.cell_size / 4, 20001)
        pts = np.asarray(point, dtype=float)[:, None] + normal[:, None] * s
        d = np.asarray(solid.get_distance_numpy(pts[0], pts[1], pts[2]))
        inside = s[d < 0]
        return inside.max() - inside.min()

    def test_cell_size_is_the_period(self):
        g = TPMSSolid("Gyroid", cell_size=7.0, thickness=0.5)
        rng = np.random.default_rng(3)
        for p in rng.uniform(-10, 10, (20, 3)):
            assert g.get_distance(p) == pytest.approx(g.get_distance(p + (7.0, 0, 0)), abs=1e-9)
            assert g.get_distance(p) == pytest.approx(g.get_distance(p + (0, 0, -14.0)), abs=1e-9)

    @pytest.mark.parametrize("thickness", [0.5, 1.0, 2.0])
    def test_schwarz_p_wall_thickness_in_model_units(self, thickness):
        # cos(kx) + cos(ky) + cos(kz) vanishes at (c/4, c/4, c/4), normal (1, 1, 1).
        solid = TPMSSolid("SchwarzP", cell_size=10.0, thickness=thickness)
        measured = self._wall_thickness(solid, (2.5, 2.5, 2.5), (1, 1, 1))
        assert measured == pytest.approx(thickness, rel=0.03)

    def test_gyroid_wall_thickness_at_origin(self):
        # The gyroid passes through the origin with normal (1, 1, 1).
        solid = TPMSSolid("Gyroid", cell_size=10.0, thickness=1.0)
        measured = self._wall_thickness(solid, (0, 0, 0), (1, 1, 1))
        assert measured == pytest.approx(1.0, rel=0.03)

    def test_thickness_field_grades_the_wall(self):
        ramp = Remap(VolPlane(Plane((0, 0, 0), (1, 0, 0))), (-50.0, 50.0), (0.5, 2.5))
        solid = TPMSSolid("SchwarzP", cell_size=10.0, thickness=ramp)
        thin = self._wall_thickness(solid, (-50 + 2.5, 2.5, 2.5), (1, 1, 1))
        thick = self._wall_thickness(solid, (50 - 7.5, 2.5, 2.5), (1, 1, 1))
        assert thin == pytest.approx(ramp.get_distance((-47.5, 0, 0)), rel=0.05)
        assert thick == pytest.approx(ramp.get_distance((42.5, 0, 0)), rel=0.05)

    def test_network_modes_are_complementary(self):
        a = TPMSSolid("IWP", 10.0, mode="network")
        b = TPMSSolid("IWP", 10.0, mode="network", invert=True)
        rng = np.random.default_rng(4)
        for p in rng.uniform(-10, 10, (50, 3)):
            assert a.get_distance(p) == pytest.approx(-b.get_distance(p))

    def test_network_offset_raises_volume_fraction(self):
        x, y, z = np.ogrid[0:10:40j, 0:10:40j, 0:10:40j]
        lean = TPMSSolid("SchwarzP", 10.0, mode="network", offset=-1.0)
        dense = TPMSSolid("SchwarzP", 10.0, mode="network", offset=1.0)
        assert (dense.get_distance_numpy(x, y, z) < 0).mean() > (lean.get_distance_numpy(x, y, z) < 0).mean()

    def test_frame_rotates_the_lattice(self):
        frame = Frame((1, 2, 3), (0, 1, 0), (-1, 0, 0))
        rotated = TPMSSolid("Gyroid", 10.0, 1.0, frame=frame)
        plain = TPMSSolid("Gyroid", 10.0, 1.0)
        # world point = origin + 4 * xaxis + 1 * yaxis  <->  local (4, 1, 0)
        assert rotated.get_distance((1 - 1, 2 + 4, 3)) == pytest.approx(plain.get_distance((4, 1, 0)))

    @pytest.mark.parametrize("kwargs", [{"cell_size": 0}, {"mode": "skeletal"}, {"frame": (0, 0, 0)}])
    def test_rejects_bad_parameters(self, kwargs):
        with pytest.raises((ValueError, TypeError)):
            TPMSSolid("Gyroid", **{"cell_size": 10.0, **kwargs})


class TestRemap:
    def test_endpoints_and_clamping(self):
        r = Remap(VolPlane(Plane((0, 0, 0), (0, 0, 1))), (0.0, 10.0), (4.0, 2.0))
        assert r.get_distance((0, 0, 0)) == pytest.approx(4.0)
        assert r.get_distance((0, 0, 5)) == pytest.approx(3.0)
        assert r.get_distance((0, 0, 10)) == pytest.approx(2.0)
        assert r.get_distance((0, 0, -99)) == pytest.approx(4.0)
        assert r.get_distance((0, 0, 99)) == pytest.approx(2.0)

    def test_smooth_ease_keeps_midpoint_and_flattens_ends(self):
        plane = VolPlane(Plane((0, 0, 0), (0, 0, 1)))
        smooth = Remap(plane, (0.0, 10.0), (0.0, 1.0), "smooth")
        linear = Remap(plane, (0.0, 10.0), (0.0, 1.0))
        assert smooth.get_distance((0, 0, 5)) == pytest.approx(0.5)
        assert smooth.get_distance((0, 0, 1)) < linear.get_distance((0, 0, 1))

    def test_rejects_empty_source_range(self):
        with pytest.raises(ValueError):
            Remap(VolPlane(Plane((0, 0, 0), (0, 0, 1))), (1.0, 1.0), (0.0, 1.0))


class TestVoronoiBlocking:
    """The blocked evaluation must be exact, not approximate."""

    @staticmethod
    def _brute(points, thickness, x, y, z, walls=True):
        from compas_vol.microstructures import voronoi as module

        coords = np.asarray(points, dtype=float)
        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
        px, py, pz = (np.broadcast_to(c, shape) for c in (x, y, z))
        wall, _ = module._walls(coords, px, py, pz)
        return wall - thickness / 2 if walls else thickness / 2 - wall

    @pytest.mark.parametrize("seed", range(4))
    @pytest.mark.parametrize("walls", [True, False])
    def test_matches_walking_every_seed(self, seed, walls):
        rng = np.random.default_rng(seed)
        count = int(rng.integers(24, 200))
        scale = float(rng.choice([5.0, 200.0]))
        points = rng.uniform(-scale, scale, (count, 3))
        res = int(rng.integers(34, 50))  # more than one block per axis
        v = Voronoi(points.tolist(), scale * 0.05, walls=walls)
        x, y, z = np.ogrid[-scale : scale : res * 1j, -scale : scale : res * 1j, -scale : scale : res * 1j]
        np.testing.assert_allclose(
            v.get_distance_numpy(x, y, z),
            self._brute(points, v.thickness, x, y, z, walls),
            rtol=1e-12,
            atol=1e-12,
        )

    def test_coincident_seeds_do_not_break_the_bounds(self):
        """Duplicate seeds give degenerate bisectors and an infinite field."""
        points = [(0.0, 0.0, 0.0)] * 30
        v = Voronoi(points, 1.0)
        x, y, z = np.ogrid[-5:5:36j, -5:5:36j, -5:5:36j]
        field = np.asarray(v.get_distance_numpy(x, y, z))
        assert np.isinf(field).all()

    def test_scalar_and_blocked_grid_agree(self):
        rng = np.random.default_rng(11)
        points = rng.uniform(-40, 40, (60, 3))
        v = Voronoi(points.tolist(), 2.0)
        coords = np.linspace(-45, 45, 40)
        x, y, z = np.ogrid[-45:45:40j, -45:45:40j, -45:45:40j]
        grid = np.asarray(v.get_distance_numpy(x, y, z))
        scalar = np.array([[[v.get_distance((a, b, c)) for c in coords] for b in coords] for a in coords])
        np.testing.assert_allclose(grid, scalar, rtol=1e-11, atol=1e-11)

    def test_both_block_formulations_agree(self):
        """The threaded path shapes the work differently; same field, though."""
        from concurrent.futures import ThreadPoolExecutor

        rng = np.random.default_rng(5)
        points = rng.uniform(-40, 40, (80, 3))
        v = Voronoi(points.tolist(), 2.5)
        x, y, z = np.ogrid[-45:45:70j, -45:45:70j, -45:45:70j]

        on_main = np.asarray(v.get_distance_numpy(x, y, z))
        with ThreadPoolExecutor(2) as pool:
            in_worker = np.asarray(pool.submit(v.get_distance_numpy, x, y, z).result())

        np.testing.assert_array_equal(on_main, in_worker)
        np.testing.assert_allclose(on_main, self._brute(points, 2.5, x, y, z), rtol=1e-12, atol=1e-12)


class TestOffset:
    def test_constant_offset_grows_and_shrinks(self):
        ball = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        assert Offset(ball, 2.0).get_distance((7, 0, 0)) == pytest.approx(0.0)
        assert Offset(ball, -2.0).get_distance((3, 0, 0)) == pytest.approx(0.0)

    def test_driven_offset_varies_through_space(self):
        """Offset by z: a sphere that bulges at the top and pinches at the bottom."""
        ball = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        by_height = Remap(VolPlane(Plane((0, 0, 0), (0, 0, 1))), (-5.0, 5.0), (-1.0, 1.0))
        shape = Offset(ball, by_height)
        assert shape.get_distance((0, 0, 6)) == pytest.approx(0.0)        # 1 mm out at the top
        # At z = -s the offset is -1 + (5 - s) / 5 = -s/5, so the surface is
        # where s - 5 = -s/5: at s = 25/6.
        assert shape.get_distance((0, 0, -25.0 / 6.0)) == pytest.approx(0.0)
