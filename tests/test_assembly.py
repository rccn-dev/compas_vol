"""Segmentation, joints, and getting a mesh into a field.

Three capabilities that arrived together because they answer one question:
how a model larger than a print bed, or larger than memory, gets made.
"""

import numpy as np
import pytest
from compas.datastructures import Mesh
from compas.geometry import Box, Sphere

from compas_vol.assembly import Pins, place_cuts, section_cost, segment
from compas_vol.combinations import Intersection
from compas_vol.combinations import Subtraction
from compas_vol.meshing import normalize_bounds
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Conform
from compas_vol.primitives import VolBox, VolCylinder, VolGrid, VolSphere


# ==============================================================================
# a mesh as a field
# ==============================================================================


def _cube_distance(points, half=10.0):
    """The analytic signed distance to an axis-aligned cube."""
    q = np.abs(points) - half
    return np.linalg.norm(np.maximum(q, 0.0), axis=-1) + np.minimum(np.max(q, axis=-1), 0.0)


def test_mesh_field_matches_the_analytic_solid():
    """A cube mesh has to measure what a cube measures."""
    grid = VolGrid.from_mesh(Mesh.from_shape(Box(20.0)), resolution=48)
    points = np.array([[0, 0, 0], [5, 0, 0], [0, 0, 9], [15, 0, 0], [0, 12, 0], [11, 11, 11]], dtype=float)
    measured = np.array([grid.get_distance(p) for p in points])
    assert np.allclose(measured, _cube_distance(points), atol=0.6)


def test_mesh_field_gets_the_sign_right_everywhere():
    """One wrong cell is a hole in the solid, so this is the check that matters."""
    grid = VolGrid.from_mesh(Mesh.from_shape(Box(20.0)), resolution=40)
    points = np.random.default_rng(0).uniform(-14, 14, (500, 3))
    measured = np.array([grid.get_distance(p) for p in points])
    exact = _cube_distance(points)
    # Cells within a voxel of the surface may legitimately disagree.
    away = np.abs(exact) > max(grid.spacing)
    assert np.array_equal(measured[away] < 0, exact[away] < 0)


def test_mesh_field_handles_a_hole():
    """Parity has to survive a solid you can see through."""
    from compas.geometry import Torus

    grid = VolGrid.from_mesh(Mesh.from_shape(Torus(12.0, 4.0)), resolution=56)
    assert grid.get_distance([0, 0, 0]) > 0        # the hole is outside
    assert grid.get_distance([12, 0, 0]) < 0       # the tube is inside
    assert grid.get_distance([30, 0, 0]) > 0       # and so is the outside


def test_mesh_field_is_not_fooled_by_a_fanned_quad():
    """A ray along the (1, 1) diagonal lands on the shared edge of a fanned quad.

    Nudging both axes equally keeps it there, the edge is counted twice, and
    every axis-aligned box in the package reads inside-out. This is the
    regression test for that.
    """
    grid = VolGrid.from_mesh(Mesh.from_shape(Box(20.0)), resolution=32)
    assert grid.get_distance([0, 0, 0]) < 0


# ==============================================================================
# a field that follows a surface
# ==============================================================================


def test_conform_substitutes_the_guide_distance():
    gyroid = TPMSSolid("Gyroid", cell_size=10.0, thickness=2.0)
    guide = VolSphere(Sphere(20.0))
    shell = Conform(gyroid, guide, axis=2, scale=1.5, offset=0.25)

    point = [3.0, 4.0, 12.0]
    expected = gyroid.get_distance([3.0, 4.0, 1.5 * guide.get_distance(point) + 0.25])
    assert shell.get_distance(point) == pytest.approx(expected)


def test_conform_follows_the_surface_not_the_world_axis():
    """The whole point: the pattern repeats in shells, not in flat layers."""
    shell = Conform(TPMSSolid("Gyroid", 10.0, 2.0), VolSphere(Sphere(20.0)), axis=2)
    # Top and bottom of the guide are 40 mm apart in Z and identical here.
    assert shell.get_distance([0, 0, 20]) == pytest.approx(shell.get_distance([0, 0, -20]))
    # And so is any pair at the same depth below the surface.
    assert shell.get_distance([0, 0, 14]) == pytest.approx(shell.get_distance([0, 0, -14]))


def test_conform_rejects_a_bad_axis():
    with pytest.raises(ValueError):
        Conform(VolSphere(Sphere(1.0)), VolSphere(Sphere(2.0)), axis=3)


# ==============================================================================
# segmentation
# ==============================================================================


def test_pieces_tile_the_bounds_without_gaps_or_overlap():
    bounds = (-150.0, -100.0, -50.0, 150.0, 100.0, 50.0)
    assembly = segment(VolSphere(Sphere(140.0)), bounds, piece=120.0)

    assert assembly.shape == (3, 2, 1)
    assert len(assembly) == 6
    for axis in range(3):
        low = min(piece.bounds[axis] for piece in assembly)
        high = max(piece.bounds[axis + 3] for piece in assembly)
        assert low == pytest.approx(bounds[axis])
        assert high == pytest.approx(bounds[axis + 3])


def test_pieces_are_never_larger_than_asked_for():
    assembly = segment(VolSphere(Sphere(300.0)), bounds=320.0, piece=250.0)
    assert max(assembly.piece_size) <= 250.0 + 1e-9


def test_a_piece_is_empty_outside_its_own_box():
    """What makes the whole thing tractable: sampling the box is enough."""
    assembly = segment(VolSphere(Sphere(140.0)), bounds=150.0, piece=110.0)
    piece = assembly[0]
    outside = [piece.bounds[3] + 20.0, 0.0, 0.0]
    assert piece.solid.get_distance(outside) > 0


def test_clearance_leaves_a_gap_between_neighbours():
    block = VolBox(Box(300.0, 100.0, 100.0), 0.0)
    assembly = segment(block, bounds=(-160, -60, -60, 160, 60, 60),
                       piece=(110.0, 200.0, 200.0), clearance=0.4)
    low, high = assembly[(0, 0, 0)], assembly[(1, 0, 0)]
    gap = high.bounds[0] - low.bounds[3]
    assert gap == pytest.approx(0.4)
    # And the gap is real in the field, not only in the bookkeeping.
    middle = [0.5 * (low.bounds[3] + high.bounds[0]), 0.0, 0.0]
    assert low.solid.get_distance(middle) > 0
    assert high.solid.get_distance(middle) > 0


def test_the_outside_of_the_assembly_keeps_its_shape():
    """Clearance comes off internal cuts only, never off the model's own face."""
    block = VolBox(Box(300.0, 100.0, 100.0), 0.0)
    assembly = segment(block, bounds=(-160, -60, -60, 160, 60, 60),
                       piece=(110.0, 200.0, 200.0), clearance=2.0)
    assert assembly[(0, 0, 0)].bounds[0] == pytest.approx(-160.0)
    assert assembly[(2, 0, 0)].bounds[3] == pytest.approx(160.0)


def test_neighbours_are_found_across_faces_only():
    assembly = segment(VolSphere(Sphere(140.0)), bounds=150.0, piece=110.0)
    axes = [axis for axis, _ in assembly.neighbours(assembly[(0, 0, 0)])]
    assert sorted(axes) == [0, 1, 2]        # a corner piece has three


def test_cost_shows_why_segmenting_is_worth_it():
    assembly = segment(VolSphere(Sphere(3000.0)), bounds=3100.0, piece=400.0)
    cost = assembly.cost(resolution=400)
    assert cost["per_piece"] < cost["whole_model"] / 100
    assert cost["pieces"] > 100


# ==============================================================================
# joints
# ==============================================================================


def _pinned():
    block = VolBox(Box(300.0, 100.0, 100.0), 0.0)
    return segment(block, bounds=(-160, -60, -60, 160, 60, 60), piece=(110.0, 200.0, 200.0),
                   clearance=0.4, joint=Pins(diameter=8.0, depth=5.0, fit=0.15, limit=3))


def test_every_joint_has_one_pin_and_one_socket():
    assembly = _pinned()
    roles = [joint["role"] for piece in assembly for joint in piece.joints]
    assert roles.count("pin") == roles.count("socket")
    assert roles.count("pin") == 6          # two cuts, three pins each


def test_the_pin_stands_proud_and_the_socket_receives_it():
    assembly = _pinned()
    low, high = assembly[(0, 0, 0)], assembly[(1, 0, 0)]
    centre = low.joints[0]["at"]
    beyond = [low.bounds[3] + 3.0, centre[1], centre[2]]

    assert low.solid.get_distance(beyond) < 0       # pin material past the cut
    assert high.solid.get_distance(beyond) > 0      # and a void waiting for it


def test_the_socket_is_wider_than_the_pin_by_the_fit():
    assembly = _pinned()
    low, high = assembly[(0, 0, 0)], assembly[(1, 0, 0)]
    centre = low.joints[0]["at"]
    at = [low.bounds[3] + 3.0, centre[1] + 4.0 + 0.10, centre[2]]
    assert high.solid.get_distance(at) > 0          # inside a 4.15 mm socket
    assert low.solid.get_distance(at) > 0           # outside a 4.00 mm pin


def test_pins_are_only_placed_where_there_is_material():
    """A pin needs a solid to stand in, and most of a porous model is not one."""
    solid = VolBox(Box(300.0, 100.0, 100.0), 0.0)
    hollow = TPMSSolid("Gyroid", cell_size=25.0, thickness=1.0)

    common = dict(bounds=(-160, -60, -60, 160, 60, 60), piece=(110.0, 200.0, 200.0),
                  joint=Pins(diameter=8.0, depth=5.0, margin=2.0, limit=6))
    dense = sum(len(p.joints) for p in segment(solid, **common))
    thin = sum(len(p.joints) for p in segment(hollow, **common))
    assert dense > thin


def test_segment_and_bounds_agree_with_the_sampler():
    """Piece bounds have to be the form the rest of the package accepts."""
    assembly = segment(VolSphere(Sphere(140.0)), bounds=150.0, piece=110.0)
    for piece in assembly:
        assert normalize_bounds(piece.bounds) == piece.bounds


def test_check_finds_the_pieces_that_come_apart():
    """Cutting a lattice on a plane leaves fragments; the gate has to see them."""
    pytest.importorskip("skfmm", reason="needs the processes extra")
    lattice = TPMSSolid("Gyroid", cell_size=22.0, thickness=2.0)
    assembly = segment(Intersection(lattice, VolBox(Box(160.0), 0.0)),
                       bounds=(-90, -90, -90, 90, 90, 90), piece=95.0)
    result = assembly.check(resolution=64, min_wall=1.5)
    assert set(result["reports"]) == {piece.name for piece in assembly}
    assert result["loose"], "a cut gyroid should leave loose fragments somewhere"
    # and they are slivers, not a third of the part
    assert max(share for _, _, share in result["loose"]) < 0.25


# ==============================================================================
# cells: pieces that follow the construction rather than a grid
# ==============================================================================


def _slab():
    return VolBox(Box(1000.0, 600.0, 100.0), 0.0)


SLAB_BOUNDS = (-500, -300, -50, 500, 300, 50)


def _t_junction():
    """One long piece on the left, two stacked on the right: a T where they meet."""
    return [
        {"bounds": (-500, -300, -50, 0, 300, 50), "name": "long", "role": "beam"},
        {"bounds": (0, -300, -50, 500, 0, 50), "name": "low", "role": "panel"},
        {"bounds": (0, 0, -50, 500, 300, 50), "name": "high", "role": "panel"},
    ]


def test_cells_keep_their_names_and_roles():
    assembly = segment(_slab(), SLAB_BOUNDS, cells=_t_junction())
    assert [p.name for p in assembly] == ["long", "low", "high"]
    assert [p.role for p in assembly] == ["beam", "panel", "panel"]
    assert assembly.shape is None
    assert "cut from cells" in assembly.manifest()


def test_cells_find_every_shared_face_including_a_t():
    assembly = segment(_slab(), SLAB_BOUNDS, cells=_t_junction())
    shared = {(f["low"].name, f["high"].name, f["axis"]) for f in assembly.interfaces}
    assert shared == {("long", "low", 0), ("long", "high", 0), ("low", "high", 1)}
    assert {p.name for _, p in assembly.neighbours(assembly.find("long"))} == {"low", "high"}


def test_cells_take_clearance_off_shared_faces_only():
    assembly = segment(_slab(), SLAB_BOUNDS, cells=_t_junction(), clearance=4.0)
    long, low, high = (assembly.find(n) for n in ("long", "low", "high"))
    assert long.bounds[3] == pytest.approx(-2.0) and long.bounds[0] == pytest.approx(-500.0)
    assert low.bounds[0] == pytest.approx(2.0) and low.bounds[4] == pytest.approx(-2.0)
    assert high.bounds[1] == pytest.approx(2.0) and high.bounds[4] == pytest.approx(300.0)


def test_pins_go_on_every_shared_face_of_a_t():
    assembly = segment(_slab(), SLAB_BOUNDS, cells=_t_junction(), clearance=0.4,
                       joint=Pins(diameter=10.0, depth=6.0, spacing=100.0, margin=5.0, limit=2))
    joints = {p.name: sorted((j["role"], j["with_"]) for j in p.joints) for p in assembly}
    assert ("pin", "low") in joints["long"] and ("pin", "high") in joints["long"]
    assert ("socket", "long") in joints["low"] and ("pin", "high") in joints["low"]
    assert all(p.features for p in assembly)


def _frame(point):
    from compas.geometry import Frame

    return Frame(point, (1, 0, 0), (0, 1, 0))


def test_place_cuts_never_exceeds_the_piece_size():
    cuts = place_cuts(0.0, 10000.0, 3000.0, cost=lambda x: (x % 1700.0), shift=500.0, step=50.0)
    edges = [0.0] + cuts + [10000.0]
    assert len(cuts) == 3
    assert max(b - a for a, b in zip(edges[:-1], edges[1:])) <= 3000.0


def test_section_cost_counts_what_the_cut_misses():
    from compas.geometry import Cylinder

    slab = Subtraction(VolBox(Box(400, 200, 40), 0.0), VolCylinder(Cylinder(40, 100, frame=_frame((0, 0, 0)))))
    # The rectangle sits just inside the slab, so only the hole is missed.
    through = section_cost(slab, 0, 0.0, (-99, -19, 99, 19), 1.0)
    beside = section_cost(slab, 0, 120.0, (-99, -19, 99, 19), 1.0)
    assert beside == 0.0
    assert through == pytest.approx(80 * 38, rel=0.05)
    assert section_cost(slab, 0, 300.0, (-100, -20, 100, 20), 5.0) == float("inf")


# ==============================================================================
# baking: a process run piece by piece, with a halo
# ==============================================================================


def _eroded_slab():
    pytest.importorskip("skfmm", reason="needs the processes extra")
    slab = VolBox(Box(200.0, 100.0, 40.0), 0.0)
    return Subtraction(slab, Intersection(TPMSSolid("Gyroid", 30.0, 8.0), VolBox(Box(400, 400, 24), 0.0)))


def _wear(field):
    from compas_vol.processes import abrasion

    return abrasion(field, depth=1.5, steps=4, length=6.0)


def test_neighbours_baked_with_a_halo_agree_at_the_seam():
    model = _eroded_slab()
    assembly = segment(model, (-100, -50, -20, 100, 50, 20), piece=(100.0, 100.0, 40.0))
    left, right = assembly
    a = left.process_field(_wear, voxel=2.0, halo=16.0).to_volume()
    b = right.process_field(_wear, voxel=2.0, halo=16.0).to_volume()
    y, z = np.mgrid[-49:49:50j, -19:19:20j]
    da, db = (g.get_distance_numpy(np.zeros_like(y), y, z) for g in (a, b))
    assert ((da < 0) != (db < 0)).mean() < 0.01
    near = np.minimum(np.abs(da), np.abs(db)) < 4.0
    assert np.abs(da - db)[near].max() < 1.0


def test_bake_closes_the_piece_and_carries_its_joints():
    pytest.importorskip("skimage", reason="needs the meshing extra")
    pytest.importorskip("skfmm", reason="needs the processes extra")
    from compas_vol.meshing import iso_surface

    model = VolBox(Box(300.0, 100.0, 100.0), 0.0)
    assembly = segment(model, (-160, -60, -60, 160, 60, 60), piece=(110.0, 200.0, 200.0), clearance=0.4,
                       joint=Pins(diameter=8.0, depth=5.0, fit=0.15))
    middle = assembly[1]
    field = middle.bake(voxel=2.0)
    assert field.bounds[0] <= middle.bounds[0] - middle.reach
    vertices, faces = iso_surface(field.values, field.origin, field.spacing)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert (counts == 2).all()


def test_build_goes_piece_by_piece_and_seams_compares_them():
    pytest.importorskip("skfmm", reason="needs the processes extra")
    from compas_vol.assembly import Seams

    model = _eroded_slab()
    assembly = segment(model, (-100, -50, -20, 100, 50, 20), piece=(100.0, 100.0, 40.0))
    seams = Seams(assembly, step=2.0)
    built = [(piece.name, field.shape) for piece, field, _ in assembly.build(_wear, voxel=2.0, halo=16.0, seams=seams)]
    assert [name for name, _ in built] == ["p_00_00_00", "p_01_00_00"]
    summary = seams.summary()
    assert summary["faces"] == 1
    assert summary["disagreement"] < 0.01 and summary["offset"] < 1.0


def test_cost_at_a_voxel_counts_the_halo():
    assembly = segment(VolBox(Box(1000.0, 1000.0, 100.0), 0.0), (-500, -500, -50, 500, 500, 50), piece=250.0)
    bare, haloed = assembly.cost(voxel=10.0), assembly.cost(voxel=10.0, halo=50.0)
    assert bare["per_piece"] == 26 * 26 * 11
    assert haloed["per_piece"] == 36 * 36 * 21
    assert haloed["whole_model"] > haloed["per_piece"] * 4
