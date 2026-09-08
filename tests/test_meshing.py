"""Iso-surfacing and the octree."""

import importlib.util

import numpy as np
import pytest
from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.meshing import Octree
from compas_vol.meshing import generate_mesh
from compas_vol.meshing import normalize_bounds
from compas_vol.meshing import sample
from compas_vol.primitives import VolSphere
from compas_vol.utilities import dumps_tree
from compas_vol.utilities import get_iso_mesh
from compas_vol.utilities import get_iso_vfs
from compas_vol.utilities import get_vfs_from_tree

# Marching cubes lives behind the `meshing` extra; bounds handling, grid
# sampling and the octree do not need it.
requires_meshing = pytest.mark.skipif(
    importlib.util.find_spec("skimage") is None, reason="needs the meshing extra"
)


class TestBounds:
    def test_scalar_means_a_centred_cube(self):
        assert normalize_bounds(10.0) == (-10.0, -10.0, -10.0, 10.0, 10.0, 10.0)

    def test_box(self):
        assert normalize_bounds(Box(20, 20, 20)) == (-10, -10, -10, 10, 10, 10)

    def test_six_sequence(self):
        assert normalize_bounds((-1, -2, -3, 4, 5, 6)) == (-1, -2, -3, 4, 5, 6)

    def test_pairs_per_axis(self):
        assert normalize_bounds([(-1, 1), (-2, 2), (-3, 3)]) == (-1, -2, -3, 1, 2, 3)

    def test_rejects_nonsense(self):
        with pytest.raises(ValueError):
            normalize_bounds("not bounds at all")


class TestSampling:
    def test_shape_and_spacing(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        dm, origin, spacing = sample(vs, 10.0, 21)
        assert dm.shape == (21, 21, 21)
        assert origin == (-10.0, -10.0, -10.0)
        assert spacing == pytest.approx((1.0, 1.0, 1.0))

    def test_anisotropic_resolution(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        dm, _, _ = sample(vs, 10.0, (11, 21, 31))
        assert dm.shape == (11, 21, 31)


@requires_meshing
class TestGenerateMesh:
    def test_returns_a_compas_mesh(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        mesh = generate_mesh(vs, 8.0, 32)
        assert isinstance(mesh, Mesh)
        assert mesh.number_of_faces() > 0

    def test_vertices_lie_on_the_surface(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        mesh = generate_mesh(vs, 8.0, 64)
        pts = np.array([mesh.vertex_coordinates(v) for v in mesh.vertices()])
        radii = np.linalg.norm(pts, axis=1)
        np.testing.assert_allclose(radii, 5.0, atol=0.05)

    def test_mesh_is_positioned_at_the_world_origin_of_the_object(self):
        """Marching cubes yields grid-relative coordinates.

        The COMPAS 1 helpers never added the grid origin back, so every mesh
        came out translated into the positive octant.
        """
        centre = Point(6, -3, 2)
        vs = VolSphere(Sphere(4, point=centre))
        mesh = generate_mesh(vs, ((-2, 10), (-9, 3), (-4, 8)), 48)
        pts = np.array([mesh.vertex_coordinates(v) for v in mesh.vertices()])
        np.testing.assert_allclose(pts.mean(axis=0), list(centre), atol=0.1)

    def test_level_offsets_the_surface(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        mesh = generate_mesh(vs, 10.0, 64, level=2.0)
        pts = np.array([mesh.vertex_coordinates(v) for v in mesh.vertices()])
        np.testing.assert_allclose(np.linalg.norm(pts, axis=1), 7.0, atol=0.05)


@requires_meshing
class TestLegacyUtilities:
    def test_compas1_bounds_form_still_works(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        mesh = get_iso_mesh(vs, [(-8, 8, 32), (-8, 8, 32), (-8, 8, 32)])
        assert mesh.number_of_faces() > 0

    def test_get_iso_vfs_matches_explicit_resolution(self):
        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        a, _ = get_iso_vfs(vs, [(-8, 8, 32), (-8, 8, 32), (-8, 8, 32)])
        b, _ = get_iso_vfs(vs, 8.0, 32)
        np.testing.assert_allclose(a, b)

    def test_rpc_roundtrip_uses_json_not_eval(self):
        """The COMPAS 1 transport eval()'d a repr string."""
        vs = VolSphere(Sphere(5, point=Point(1, 2, 3)))
        payload = dumps_tree(vs)
        assert payload.strip().startswith("{")

        verts, faces = get_vfs_from_tree(payload, [(-8, 8, 24), (-8, 8, 24), (-8, 8, 24)])
        assert isinstance(verts, list) and isinstance(faces, list)
        assert len(verts) > 0


class TestOctree:
    def test_builds_and_refines_towards_the_surface(self):
        vs = VolSphere(Sphere(30, point=Point(0, 0, 0)))
        tree = Octree(vs, 100.0, 3)
        tree.build()
        assert len(tree.leaves()) > 8

    def test_surface_leaves_straddle_the_boundary(self):
        vs = VolSphere(Sphere(30, point=Point(0, 0, 0)))
        tree = Octree(vs, 100.0, 4)
        tree.build()
        leaves = tree.surface_leaves()
        assert leaves
        half_diagonal = np.sqrt(3) * leaves[0].edgelength / 2
        for leaf in leaves:
            assert abs(vs.get_distance(leaf.point)) < half_diagonal

    def test_to_boxes(self):
        vs = VolSphere(Sphere(30, point=Point(0, 0, 0)))
        tree = Octree(vs, 100.0, 3)
        tree.build()
        boxes = tree.to_boxes()
        assert boxes and all(isinstance(b, Box) for b in boxes)

    def test_level_stays_an_integer(self):
        """The COMPAS 1 level setter cast to float, breaking depth comparison."""
        from compas_vol.meshing import OctNode

        node = OctNode(0, 0, 0, 10.0, 0)
        node.level = 3
        assert node.level == 3
        assert isinstance(node.level, int)
