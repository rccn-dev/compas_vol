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
