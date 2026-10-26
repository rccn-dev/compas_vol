"""Processes: the evolution operator, its terms, and the presets built on them.

Checks are analytic wherever there is an analytic answer -- a sphere's
curvature, the distance a uniform speed moves a surface -- and otherwise
check the property the process exists for: that abrasion rounds, that
fingering roughens, that noise does not change when the grid does.
"""

import numpy as np
import pytest
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Union
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolGrid
from compas_vol.primitives import VolSphere

pytest.importorskip("skfmm", reason="needs the processes extra")

from compas_vol.processes import Field  # noqa: E402
from compas_vol.processes import abrasion  # noqa: E402
from compas_vol.processes import closed  # noqa: E402
from compas_vol.processes import accretion  # noqa: E402
from compas_vol.processes import branching  # noqa: E402
from compas_vol.processes import differential  # noqa: E402
from compas_vol.processes import evolve  # noqa: E402
from compas_vol.processes import fbm  # noqa: E402
from compas_vol.processes import fingering  # noqa: E402
from compas_vol.processes import hardness  # noqa: E402
from compas_vol.processes import jointing  # noqa: E402
from compas_vol.processes import lattice  # noqa: E402
from compas_vol.processes import opened  # noqa: E402
from compas_vol.processes import pitting  # noqa: E402
from compas_vol.processes import reaction_diffusion  # noqa: E402
from compas_vol.processes import redistance  # noqa: E402
from compas_vol.processes import runoff  # noqa: E402
from compas_vol.processes import spinodal  # noqa: E402
from compas_vol.processes import strata  # noqa: E402
from compas_vol.processes import terms  # noqa: E402
from compas_vol.processes import value_noise  # noqa: E402


@pytest.fixture(scope="module")
def ball():
    """A 20 mm sphere on a 41^3 grid: 1.5 mm voxels."""
    return Field.from_object(VolSphere(Sphere(20, point=Point(0, 0, 0))), bounds=30.0, resolution=41)


def shape_index(field):
    """Surface area over volume^(2/3): 4.84 for a sphere, more for anything folded."""
    from skimage.measure import marching_cubes

    vertices, triangles, _, _ = marching_cubes(field.values, 0.0, spacing=field.spacing)
    a, b, c = vertices[triangles[:, 0]], vertices[triangles[:, 1]], vertices[triangles[:, 2]]
    area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2)
    volume = float((field.values < 0).sum()) * np.prod(field.spacing)
    return area / volume ** (2 / 3)


class TestField:
    def test_grid_metadata(self, ball):
        assert ball.shape == (41, 41, 41)
        assert ball.voxel == pytest.approx(60 / 40)
        assert ball.bounds == pytest.approx((-30, -30, -30, 30, 30, 30))
        assert 0.1 < ball.solid_fraction() < 0.2

    def test_coordinates_are_world_positions(self, ball):
        x, y, z = ball.coordinates()
        assert x.shape == (41, 1, 1) and y.shape == (1, 41, 1) and z.shape == (1, 1, 41)
        assert float(x.min()) == pytest.approx(-30.0)

    def test_sampling_redistances_a_non_metric_field(self):
        """A blended tree is not metric; Field.from_object fixes that."""
        blob = Union(VolSphere(Sphere(10, point=Point(-4, 0, 0))), VolSphere(Sphere(10, point=Point(4, 0, 0))))
        field = Field.from_object(blob, bounds=20.0, resolution=32)
        gradients = np.gradient(field.values, *field.spacing)
        magnitude = np.sqrt(sum(g * g for g in gradients))
        assert np.median(magnitude) == pytest.approx(1.0, abs=0.02)

    def test_empty_grid_covers_the_bounds(self):
        field = Field.empty((-10, -20, -30, 10, 20, 30), 16)
        assert field.shape == (16, 16, 16)
        assert field.bounds == pytest.approx((-10, -20, -30, 10, 20, 30))

    def test_displaced_moves_the_surface_by_the_amount(self, ball):
        moved = ball.displaced(2.0)
        assert moved.to_volume().get_distance([25, 0, 0]) == pytest.approx(7.0, abs=0.1)

    def test_history_is_carried_and_readable(self, ball):
        worn = abrasion(ball, depth=1.0, steps=2)
        assert [entry["operation"] for entry in worn.history][-1] == "abrasion"
        assert "sample" in worn.provenance() and "abrasion(" in worn.provenance()

    def test_rejects_a_non_grid(self):
        with pytest.raises(ValueError):
            Field(np.zeros((4, 4)), (0, 0, 0), (1, 1, 1))


class TestRedistance:
    def test_restores_unit_gradient_and_keeps_the_surface(self, ball):
        distorted = ball.values * (1.0 + 0.5 * np.sin(ball.values))
        fixed = redistance(distorted, ball.spacing)
        gradients = np.gradient(fixed, *ball.spacing)
        assert np.median(np.sqrt(sum(g * g for g in gradients))) == pytest.approx(1.0, abs=0.02)
        # The zero set is where it was: signs agree everywhere away from it.
        far = np.abs(ball.values) > ball.voxel
        assert (np.sign(fixed[far]) == np.sign(distorted[far])).mean() > 0.999

    def test_without_a_surface_it_says_so(self, ball):
        with pytest.raises(ValueError, match="no surface"):
            redistance(np.abs(ball.values) + 1.0, ball.spacing)


class TestEvolve:
    @pytest.mark.parametrize("rate,expected", [(0.25, 2.0), (-0.25, -2.0)])
    def test_uniform_speed_moves_the_surface_by_speed_times_steps(self, ball, rate, expected):
        """Positive erodes, negative grows, and the distance is exactly stated.

        Accuracy is first order in the voxel: 6% at 1.5 mm voxels here, 0.5%
        at 0.67 mm.
        """
        moved = evolve(ball, terms.Uniform(rate), steps=8)
        probe = moved.to_volume().get_distance([25, 0, 0]) - ball.to_volume().get_distance([25, 0, 0])
        assert probe == pytest.approx(expected, abs=0.15)

    def test_a_step_is_capped_at_a_fraction_of_a_voxel(self, ball):
        """However fast the speed says, the surface may not outrun the grid."""
        moved = evolve(ball, terms.Uniform(1e3), steps=1, limit=0.5)
        shift = np.median(moved.values - ball.values)
        assert shift == pytest.approx(0.5 * ball.voxel, rel=0.25)

    def test_the_input_is_left_alone(self, ball):
        before = ball.values.copy()
        evolve(ball, terms.Uniform(0.2), steps=2)
        np.testing.assert_array_equal(before, ball.values)

    def test_redistancing_less_often_still_runs(self, ball):
        moved = evolve(ball, terms.Uniform(0.2), steps=4, redistance_every=2)
        assert moved.solid_fraction() < ball.solid_fraction()


class TestTerms:
    def test_curvature_of_a_sphere_is_two_over_the_radius(self, ball):
        """The analytic case, and the one that catches a wrong length scale."""
        near = np.abs(ball.values) < ball.voxel
        measured = terms.curvature_of(ball)[near]
        assert np.median(measured) == pytest.approx(2 / 20, rel=0.1)

    def test_convexity_and_concavity_split_the_sign(self, ball):
        near = np.abs(ball.values) < ball.voxel
        convex = terms.Convexity(length=10.0)(ball)[near]
        concave = terms.Concavity(length=10.0)(ball)[near]
        assert convex.min() >= 0 and convex.max() <= 1
        assert np.median(convex) > 0.4        # a sphere is convex everywhere
        assert np.median(concave) == 0.0

    def test_shelter_is_higher_inside_a_notch(self):
        """A hollow shelters; a nose does not."""
        block = VolBox(Box(30, 30, 30), 0.0)
        notched = Field.from_object(block, bounds=25.0, resolution=48)
        shelter = terms.Shelter(reach=5.0)(notched)
        assert 0.0 <= shelter.min() and shelter.max() <= 1.0
        assert shelter[np.abs(notched.values) < notched.voxel].max() > 0.0

    def test_algebra_combines_numbers_and_terms(self, ball):
        combined = terms.Uniform(1.0) * 2.0 + 1.0
        assert np.allclose(combined(ball), 3.0)
        assert np.allclose((-terms.Uniform(1.0))(ball), -1.0)
        assert np.allclose((3.0 - terms.Uniform(1.0))(ball), 2.0)

    def test_smoothing_reduces_variation(self, ball):
        rough = terms.Values(np.random.default_rng(0).standard_normal(ball.shape))
        assert terms.Smooth(rough, length=6.0)(ball).std() < rough(ball).std()

    def test_a_signal_of_the_wrong_shape_is_refused(self, ball):
        with pytest.raises(ValueError, match="shaped"):
            terms.Values(np.zeros((3, 3, 3)))(ball)


class TestNoise:
    def test_same_seed_same_values(self):
        a = value_noise(*np.ogrid[0:10:9j, 0:10:9j, 0:10:9j], cell_size=4.0, seed=1)
        b = value_noise(*np.ogrid[0:10:9j, 0:10:9j, 0:10:9j], cell_size=4.0, seed=1)
        np.testing.assert_array_equal(a, b)
        assert np.abs(a).max() <= 1.0

    def test_different_seeds_differ(self):
        grid = np.ogrid[0:10:9j, 0:10:9j, 0:10:9j]
        assert not np.allclose(value_noise(*grid, seed=1), value_noise(*grid, seed=2))

    def test_the_same_design_at_two_resolutions_is_the_same_noise(self):
        """The property that makes a design repeatable.

        Noise drawn on the grid changes whenever the resolution does, so the
        model would change with it. Defined on world coordinates, a finer grid
        resolves the same field instead of replacing it.
        """
        coarse = np.ogrid[0:20:11j, 0:20:11j, 0:20:11j]
        fine = np.ogrid[0:20:21j, 0:20:21j, 0:20:21j]
        rough = fbm(*coarse, cell_size=8.0, octaves=3, seed=5)
        dense = fbm(*fine, cell_size=8.0, octaves=3, seed=5)
        np.testing.assert_allclose(rough, dense[::2, ::2, ::2], rtol=1e-12, atol=1e-12)

    def test_translating_the_model_translates_the_noise(self):
        here = fbm(*np.ogrid[0:10:6j, 0:10:6j, 0:10:6j], cell_size=7.0, seed=3)
        there = fbm(*np.ogrid[100:110:6j, 0:10:6j, 0:10:6j], cell_size=7.0, seed=3)
        assert not np.allclose(here, there)   # it is a field in space, not a texture


class TestWeathering:
    def test_abrasion_eats_corners_faster_than_faces(self):
        """What abrasion is for, measured against the same process without it.

        Comparing curvature before and after would not show this: erosion
        shrinks the object, and a smaller object is more curved everywhere.
        Comparing against ``edge_bias=0`` -- the same erosion with the bias
        switched off -- isolates what the bias does.
        """
        box = Field.from_object(VolBox(Box(30, 30, 30), 0.0), bounds=25.0, resolution=48)
        before = box.to_volume()
        biased = abrasion(box, depth=3.0, steps=10, length=8.0, edge_bias=2.0).to_volume()
        even = abrasion(box, depth=3.0, steps=10, length=8.0, edge_bias=0.0).to_volume()

        corner = lambda after: after.get_distance([20, 20, 20]) - before.get_distance([20, 20, 20])  # noqa: E731
        face = lambda after: after.get_distance([0, 0, 20]) - before.get_distance([0, 0, 20])  # noqa: E731

        assert corner(biased) > 1.5 * corner(even)     # the corner goes back much further
        assert face(biased) < 1.8 * face(even)         # the face, hardly at all

    def test_differential_removes_material_and_stays_metric(self, ball):
        worn = differential(ball, depth=3.0, cell_size=20.0, seed=2)
        assert worn.solid_fraction() < ball.solid_fraction()
        gradients = np.gradient(worn.values, *worn.spacing)
        assert np.median(np.sqrt(sum(g * g for g in gradients))) == pytest.approx(1.0, abs=0.03)

    def test_pitting_is_local_where_weathering_is_general(self, ball):
        """Pits eat deeply in a few places; weathering takes a little everywhere.

        Measured as how far the deepest point runs ahead of the average: the
        feedback that makes honeycomb shows up here and nowhere else.
        """
        resistance = hardness(ball, cell_size=15.0, seed=4)
        near = np.abs(ball.values) < 2 * ball.voxel

        def concentration(result):
            removed = (result.values - ball.values)[near]
            return removed.max() / max(removed.mean(), 1e-9)

        assert concentration(pitting(ball, resistance=resistance, depth=4.0, steps=8, length=5.0)) > 3.0
        assert concentration(differential(ball, resistance=resistance, depth=4.0)) < 2.5

    def test_abrasion_takes_the_stated_depth_off_a_flat_face(self):
        """`depth` is millimetres off a flat face, not an arbitrary scale."""
        box = Field.from_object(VolBox(Box(30, 30, 30), 0.0), bounds=25.0, resolution=48)
        worn = abrasion(box, depth=3.0, steps=10, length=8.0, edge_bias=0.0)
        retreat = worn.to_volume().get_distance([0, 0, 20]) - box.to_volume().get_distance([0, 0, 20])
        assert retreat == pytest.approx(3.0, abs=0.4)

    def test_strata_leaves_bands_along_the_dip(self, ball):
        layered = strata(ball, thickness=8.0, dip=(0.0, 0.0), depth=3.0, wobble=0.0)
        removed = (layered.values - ball.values).mean(axis=(0, 1))
        # Alternating beds: the retreat profile changes sign along Z repeatedly.
        crossings = np.diff(np.sign(np.diff(removed))).astype(bool).sum()
        assert crossings >= 4

    def test_runoff_cuts_from_above(self, ball):
        rained = runoff(ball, depth=4.0)
        removed = rained.values - ball.values
        upper = removed[:, :, ball.shape[2] // 2:].mean()
        lower = removed[:, :, : ball.shape[2] // 2].mean()
        assert upper > lower

    def test_runoff_needs_something_to_erode(self):
        empty = Field.empty(10.0, 8, fill=1.0)
        with pytest.raises(ValueError, match="no solid"):
            runoff(empty)

    def test_jointing_opens_seams_through_the_mass(self, ball):
        jointed = jointing(ball, count=8, opening=3.0, seed=1)
        assert jointed.solid_fraction() < ball.solid_fraction()

    def test_jointing_accepts_placed_blocks(self, ball):
        jointed = jointing(ball, points=[(-10, 0, 0), (10, 0, 0)], opening=4.0)
        assert jointed.history[-1]["count"] == 2


class TestGrowth:
    def test_fingering_folds_instead_of_inflating(self):
        """The instability has to actually develop.

        Measured by shape index, surface area over volume to the two thirds:
        4.84 for a sphere, whatever it has grown to, and higher for anything
        folded. This is the check that fails when curvature is measured
        against the voxel size instead of a real length, or when the speed is
        clipped point by point instead of scaled -- both of which silently
        return a smooth ball.
        """
        seed = Field.from_object(VolSphere(Sphere(7, point=Point(0, 0, 0))), bounds=50.0, resolution=80)
        folded = fingering(seed, height=24.0, length=9.0, gain=1.4, wavelength=4.0)
        assert folded.solid_fraction() > seed.solid_fraction()
        # Folds need room to develop: the surface has to grow several times
        # the radius it started at before they are more than ripples.
        assert shape_index(folded) > 1.5 * shape_index(seed)

    def test_growth_distance_does_not_depend_on_resolution(self):
        """The same design at two resolutions grows the same distance.

        Advance is capped per step as a fraction of a voxel, so a step count
        means different distances on different grids. Deriving the steps from
        a height in millimetres is what keeps a design fixed.
        """
        reach = []
        for resolution in (48, 72):
            seed = Field.from_object(VolSphere(Sphere(8, point=Point(0, 0, 0))), bounds=40.0, resolution=resolution)
            grown = fingering(seed, height=9.0, length=9.0, gain=0.0)   # gain 0: pure advance
            reach.append(abs(float(grown.values.min())))
        assert reach[0] == pytest.approx(reach[1], rel=0.1)
        assert reach[0] == pytest.approx(17.0, rel=0.15)                # 8 mm seed + 9 mm

    def test_uniform_growth_stays_a_sphere(self):
        """The control: without the curvature term, the same loop just inflates."""
        seed = Field.from_object(VolSphere(Sphere(7, point=Point(0, 0, 0))), bounds=50.0, resolution=80)
        plain = fingering(seed, height=24.0, length=9.0, gain=0.0)   # no instability
        assert shape_index(plain) == pytest.approx(4.84, rel=0.1)

    def test_accretion_fills_in(self, ball):
        filled = accretion(ball, height=2.0, steps=4, reach=6.0)
        assert filled.solid_fraction() > ball.solid_fraction()

    def test_branching_makes_a_connected_tapered_network(self):
        grown = branching(bounds=30.0, resolution=40, attractors=120, step=4.0,
                          influence=20.0, kill=6.0, iterations=40, seed=1)
        assert grown.history[-1]["nodes"] > 10
        assert 0.0 < grown.solid_fraction() < 0.9

    def test_branching_says_when_nothing_can_grow(self):
        with pytest.raises(ValueError, match="Nothing grew"):
            branching(bounds=30.0, resolution=16, attractors=20, influence=0.1, iterations=5, seed=1)


class TestGenerators:
    def test_spinodal_hits_its_volume_fraction_and_percolates(self):
        """Both phases have to stay connected, or it is not a foam."""
        from scipy import ndimage

        foam = spinodal(bounds=30.0, resolution=48, feature=6.0, fraction=0.5, steps=250, seed=0)
        assert foam.solid_fraction() == pytest.approx(0.5, abs=0.1)
        for phase in (foam.values < 0, foam.values > 0):
            labels, count = ndimage.label(phase)
            largest = np.bincount(labels.ravel())[1:].max()
            assert largest > 0.9 * phase.sum()

    def test_spinodal_is_repeatable(self):
        a = spinodal(bounds=20.0, resolution=24, steps=40, seed=7)
        b = spinodal(bounds=20.0, resolution=24, steps=40, seed=7)
        np.testing.assert_array_equal(a.values, b.values)

    def test_reaction_diffusion_runs_at_its_defaults(self):
        pattern = reaction_diffusion(bounds=30.0, resolution=32, steps=400, seed=1)
        assert 0.0 < pattern.solid_fraction() < 1.0

    def test_reaction_diffusion_says_when_the_reaction_died(self):
        """Much of the feed/kill map gives nothing at all; say so plainly."""
        with pytest.raises(ValueError, match="no surface"):
            reaction_diffusion(bounds=20.0, resolution=16, feed=0.002, kill=0.2, steps=60)


class TestVolGrid:
    def test_interpolates_an_analytic_field(self):
        x, y, z = np.ogrid[-15:15:61j, -15:15:61j, -15:15:61j]
        grid = VolGrid(np.sqrt(x**2 + y**2 + z**2) - 8.0, (-15, -15, -15), (0.5, 0.5, 0.5))
        rng = np.random.default_rng(0)
        points = rng.uniform(-10, 10, (200, 3))
        expected = np.linalg.norm(points, axis=1) - 8.0
        measured = np.array([grid.get_distance(p) for p in points])
        assert np.abs(measured - expected).max() < 0.02   # trilinear error on a 0.5 mm grid

    def test_outside_the_grid_the_field_keeps_rising(self):
        x, y, z = np.ogrid[-10:10:21j, -10:10:21j, -10:10:21j]
        grid = VolGrid(np.sqrt(x**2 + y**2 + z**2) - 5.0, (-10, -10, -10), (1.0, 1.0, 1.0))
        assert grid.get_distance([30, 0, 0]) == pytest.approx(25.0, abs=0.5)
        assert grid.get_distance([60, 0, 0]) > grid.get_distance([30, 0, 0])

    def test_round_trips_through_json(self):
        from compas.data import json_dumps
        from compas.data import json_loads

        x, y, z = np.ogrid[-5:5:11j, -5:5:11j, -5:5:11j]
        grid = VolGrid(np.sqrt(x**2 + y**2 + z**2) - 3.0, (-5, -5, -5), (1.0, 1.0, 1.0))
        restored = json_loads(json_dumps(grid))
        assert restored.get_distance([0, 0, 0]) == pytest.approx(grid.get_distance([0, 0, 0]), abs=1e-6)

    def test_models_like_any_other_object(self, ball):
        """The point of the bridge: a process result goes back into a tree."""
        from compas_vol.combinations import Intersection
        from compas_vol.modifications import Shell

        part = Intersection(Shell(ball.to_volume(), 2.0, side=1.0), VolBox(Box(60, 60, 60), 0.0))
        assert part.get_distance([0, 0, 0]) > 0        # hollow at the centre
        assert part.get_distance([19, 0, 0]) < 0       # solid in the skin

    def test_baking_an_expensive_tree(self):
        blob = Union(VolSphere(Sphere(6, point=Point(-3, 0, 0))), VolSphere(Sphere(6, point=Point(3, 0, 0))))
        baked = VolGrid.from_object(blob, bounds=15.0, resolution=32)
        assert baked.get_distance([0, 0, 0]) == pytest.approx(blob.get_distance([0, 0, 0]), abs=0.6)

    def test_refuses_a_degenerate_grid(self):
        with pytest.raises(ValueError):
            VolGrid(np.zeros((2, 2)), (0, 0, 0), (1, 1, 1))
        with pytest.raises(ValueError):
            VolGrid(np.zeros((1, 4, 4)), (0, 0, 0), (1, 1, 1))


class TestDepthIsHonoured:
    """A preset asking for millimetres has to deliver them.

    :func:`evolve` will not move the surface more than half a voxel per step.
    Asked for a depth that needs more steps than were given, the presets raise
    the step count rather than quietly coming up short.
    """

    def test_too_few_steps_are_raised(self, ball):
        worn = abrasion(ball, depth=4.0, steps=2, length=8.0, edge_bias=2.0)
        assert worn.history[-1]["steps"] > 2
        assert worn.history[-2]["steps_limited"] == 0

    def test_and_the_depth_still_comes_out_right(self):
        box = Field.from_object(VolBox(Box(30, 30, 30), 0.0), bounds=25.0, resolution=48)
        worn = abrasion(box, depth=3.0, steps=1, length=8.0, edge_bias=0.0)
        retreat = worn.to_volume().get_distance([0, 0, 20]) - box.to_volume().get_distance([0, 0, 20])
        assert retreat == pytest.approx(3.0, abs=0.4)


class TestMorphology:
    """Minimum feature size as a property of the geometry, not of the render."""

    @staticmethod
    def slab(thickness, resolution=48):
        """A plate of the given thickness, lying flat."""
        return Field.from_object(
            VolBox(Box(40, 40, thickness), 0.0), bounds=(-25, -25, -12, 25, 25, 12), resolution=resolution
        )

    def test_opening_deletes_what_is_thinner_than_the_ball(self):
        with pytest.raises(ValueError, match="thicker than"):
            opened(self.slab(2.0), 2.0)      # a 2 mm plate cannot hold a 4 mm ball

    def test_opening_keeps_what_is_thicker(self):
        plate = self.slab(8.0)
        kept = opened(plate, 2.0)
        assert kept.solid_fraction() == pytest.approx(plate.solid_fraction(), rel=0.1)

    def test_opening_never_adds_material(self, ball):
        """True by construction; numerically, within a fraction of a voxel.

        Each of the two redistancing passes carries a sub-voxel error, so the
        surface comes back within about a third of a voxel of where it was.
        """
        kept = opened(ball, 2.0)
        assert (kept.values >= ball.values - 0.5 * ball.voxel).all()

    def test_opening_removes_loose_fragments(self, ball):
        """A crumb too small to hold the ball is gone, whole."""
        import numpy as np
        from scipy import ndimage

        crumbed = ball.values.copy()
        x, y, z = ball.coordinates()
        crumb = np.sqrt((x - 25) ** 2 + y**2 + z**2) - 1.2      # a 2.4 mm speck, well clear
        crumbed = np.minimum(crumbed, crumb)
        littered = ball.copy(crumbed).redistanced()
        assert ndimage.label(littered.values < 0)[1] == 2

        assert ndimage.label(opened(littered, 2.0).values < 0)[1] == 1

    @staticmethod
    def pair(gap):
        """Two spheres with a gap of the given width between them."""
        offset = 8.0 + gap / 2
        return Field.from_object(
            Union(VolSphere(Sphere(8, point=Point(-offset, 0, 0))), VolSphere(Sphere(8, point=Point(offset, 0, 0)))),
            bounds=25.0,
            resolution=48,
        )

    def test_closing_joins_gaps_narrower_than_the_ball(self):
        from scipy import ndimage

        narrow = self.pair(4.0)
        assert ndimage.label(narrow.values < 0)[1] == 2
        assert ndimage.label(closed(narrow, 3.0).values < 0)[1] == 1     # 4 mm < 6 mm: filled

    def test_closing_leaves_wider_gaps_alone(self):
        from scipy import ndimage

        wide = self.pair(6.0)
        assert ndimage.label(closed(wide, 3.0).values < 0)[1] == 2       # 6 mm: not filled

    def test_closing_never_removes_material(self):
        """True by construction, within the error of two redistancing passes."""
        wide = self.pair(6.0)
        assert (closed(wide, 3.0).values <= wide.values + wide.voxel).all()

    def test_closing_the_whole_domain_says_so(self, ball):
        with pytest.raises(ValueError, match="filled the whole domain"):
            closed(ball, 40.0)


def _slab_and_beam():
    """A 40 x 40 x 10 slab with an 8 mm beam through its middle, as a field."""
    from compas.geometry import Frame

    slab = VolBox(Box(40, 40, 10), 0.0)
    beam = VolBox(Box(8, 40, 10, frame=Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))), 0.0)
    return Field.from_object(slab, bounds=26.0, resolution=40), beam


class TestConstraints:
    def test_keep_survives_every_kind_of_process(self):
        field, beam = _slab_and_beam()
        kept = field.constrain(keep=beam)
        for result in (
            abrasion(kept, depth=6.0, edge_bias=0.0),
            pitting(kept, depth=6.0, steps=8, length=4.0, cell_size=10.0, threshold=-0.5),
            jointing(kept, count=6, opening=3.0, reach=30.0, seed=1),
            opened(kept, 6.0),
            differential(kept, depth=8.0, cell_size=10.0),
        ):
            assert result.violation()["keep"] < result.voxel
            assert result.solid_fraction() < kept.solid_fraction()

    def test_without_keep_the_same_process_takes_the_beam(self):
        field, beam = _slab_and_beam()
        worn = abrasion(field, depth=3.0, edge_bias=0.0)
        assert worn.constrain(keep=beam).violation()["keep"] == 0.0     # constrain restores it at once
        lost = (worn.values > 0) & (beam.get_distance_numpy(*worn.coordinates()) < 0)
        assert lost.any()

    def test_constraints_travel_with_copies_and_crops(self):
        field, beam = _slab_and_beam()
        kept = field.constrain(keep=beam, margin=2.0)
        part = kept.copy().cropped((-10, -10, -10, 10, 10, 10))
        assert part.keep is not None and part.keep.shape == part.shape and part.margin == 2.0

    def test_margin_fades_erosion_towards_what_is_kept(self):
        field, beam = _slab_and_beam()
        hard = abrasion(field.constrain(keep=beam), depth=4.0, edge_bias=0.0)
        soft = abrasion(field.constrain(keep=beam, margin=6.0), depth=4.0, edge_bias=0.0)
        assert soft.solid_fraction() > hard.solid_fraction()

    def test_within_stops_growth_at_the_envelope(self):
        envelope = VolSphere(Sphere(14, point=Point(0, 0, 0)))
        seed = Field.from_object(VolSphere(Sphere(10, point=Point(0, 0, 0))), bounds=20.0, resolution=41)
        grown = accretion(seed.constrain(within=envelope), height=8.0, shelter=0.0)
        assert grown.violation()["within"] < grown.voxel
        free = accretion(seed, height=8.0, shelter=0.0)
        assert free.solid_fraction() > grown.solid_fraction()

    def test_constraint_must_match_the_grid(self):
        field, _ = _slab_and_beam()
        with pytest.raises(ValueError):
            field.constrain(keep=np.zeros((3, 3, 3)))


class TestLattice:
    def test_overlapping_boxes_share_their_samples(self):
        ball = VolSphere(Sphere(10, point=Point(0, 0, 0)))
        a = Field.from_object(ball, (-12.3, -12, -12, 3.7, 12, 12), voxel=1.5, redistanced=False)
        b = Field.from_object(ball, (-4.1, -12, -12, 12, 12, 12), voxel=1.5, redistanced=False)
        overlap = (-3.0, -12, -12, 3.0, 12, 12)
        assert np.array_equal(a.cropped(overlap).values, b.cropped(overlap).values)
        assert a.cropped(overlap).origin == b.cropped(overlap).origin

    def test_lattice_covers_the_bounds(self):
        bounds, counts = lattice((0.5, 0, 0, 10, 4, 3.1), 2.0)
        assert bounds[0] <= 0.5 and bounds[5] >= 3.1 and counts == (6, 3, 3)
        with pytest.raises(ValueError):
            lattice((0, 0, 0, 1, 1, 1), 0.0)


class TestMorphologyBounds:
    def test_opening_never_adds_and_closing_never_removes(self):
        field, beam = _slab_and_beam()
        kept = field.constrain(keep=beam)
        opened_field = opened(kept, 3.0)
        assert not ((opened_field.values < -opened_field.voxel) & (kept.values > 0)).any()
        closed_field = closed(field, 3.0)
        assert not ((closed_field.values > closed_field.voxel) & (field.values < 0)).any()
