"""Iso-surfacing, STL export and the octree."""

import importlib.util
import os

import numpy as np
import pytest
from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.meshing import Octree
from compas_vol.meshing import export_stl
from compas_vol.meshing import generate_mesh
from compas_vol.meshing import generate_vertices_and_faces
from compas_vol.meshing import normalize_bounds
from compas_vol.meshing import sample
from compas_vol.meshing import write_stl
from compas_vol.primitives import VolPlane
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


class TestThreadedSampling:
    """Sampling in parallel slabs must give exactly the serial result."""

    def test_threads_match_serial(self, volobject):
        serial, origin_a, spacing_a = sample(volobject, 12.0, 24, workers=1)
        threaded, origin_b, spacing_b = sample(volobject, 12.0, 24, workers=4)
        np.testing.assert_array_equal(serial, threaded)
        assert origin_a == origin_b and spacing_a == spacing_b

    def test_anisotropic_resolution_and_bounds(self):
        field, origin, spacing = sample(VolSphere(Sphere(5)), (-6, -7, -8, 6, 7, 8), (9, 11, 13), workers=3)
        assert field.shape == (9, 11, 13)
        assert origin == (-6, -7, -8)
        assert spacing == pytest.approx((12 / 8, 14 / 10, 16 / 12))

    def test_more_workers_than_rows(self):
        field, _, _ = sample(VolSphere(Sphere(5)), 8.0, (3, 4, 5), workers=16)
        assert field.shape == (3, 4, 5)

    def test_result_is_writable(self):
        """Callers post-process the field; it must not be a broadcast view."""
        field, _, _ = sample(VolPlane(Plane((0, 0, 0), (0, 0, 1))), 8.0, 8)
        field[0, 0, 0] = 42.0
        assert field[0, 0, 0] == 42.0


@requires_meshing
class TestStl:
    def test_written_stl_reads_back_identically(self, tmp_path):
        obj = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        path = export_stl(obj, str(tmp_path / "ball.stl"), 8.0, 32)

        verts, faces = generate_vertices_and_faces(obj, 8.0, 32)
        assert os.path.getsize(path) == 84 + 50 * len(faces)

        reloaded = Mesh.from_stl(path, precision=5)
        assert reloaded.number_of_faces() == len(faces)
        assert reloaded.is_valid()
        # Every edge used twice: a closed surface survived the round trip.
        assert not list(reloaded.edges_on_boundary())

    def test_facet_normals_point_out_of_the_solid(self, tmp_path):
        """A flipped normal reads as an inside-out solid in a slicer."""
        path = export_stl(VolSphere(Sphere(5, point=Point(0, 0, 0))), str(tmp_path / "ball.stl"), 8.0, 24)
        with open(path, "rb") as f:
            f.seek(80)
            count = int(np.frombuffer(f.read(4), dtype="<u4")[0])
            facets = np.frombuffer(f.read(50 * count), dtype=np.dtype([("n", "<3f4"), ("v", "<3,3f4"), ("a", "<u2")]))
        centroids = facets["v"].mean(axis=1)
        radial = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)
        assert np.einsum("ij,ij->i", facets["n"], radial).min() > 0

    def test_matches_compas_geometry(self, tmp_path):
        obj = VolSphere(Sphere(5, point=Point(1, 2, 3)))
        ours = Mesh.from_stl(export_stl(obj, str(tmp_path / "a.stl"), 9.0, 20), precision=5)
        theirs = generate_mesh(obj, 9.0, 20)
        assert ours.number_of_faces() == theirs.number_of_faces()
        np.testing.assert_allclose(ours.centroid(), theirs.centroid(), atol=1e-4)

    def test_rejects_non_triangles(self, tmp_path):
        with pytest.raises(ValueError):
            write_stl(str(tmp_path / "quad.stl"), [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], [[0, 1, 2, 3]])

    def test_degenerate_triangle_gets_a_zero_normal(self, tmp_path):
        path = write_stl(str(tmp_path / "flat.stl"), [[0, 0, 0], [1, 0, 0], [2, 0, 0]], [[0, 1, 2]])
        assert os.path.getsize(path) == 84 + 50
