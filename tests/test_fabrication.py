"""Printability checks and their repairs.

Anchored on shapes whose answers are known: a sphere's overhang fraction is
(1 - cos 45) / 2, a hollow sphere traps exactly its inner volume, a table
starts its top in mid-air.
"""

import numpy as np
import pytest

from compas_vol.fabrication import inspect
from compas_vol.fabrication import surface_normals

VOXEL = 0.5


def grid(size=12.0, voxel=VOXEL):
    """Coordinate axes for a cube of the given half-size."""
    n = int(2 * size / voxel) + 1
    return np.ogrid[-size : size : n * 1j, -size : size : n * 1j, -size : size : n * 1j]


def ball(radius=6.0, centre=(0, 0, 0), size=12.0):
    x, y, z = grid(size)
    return np.sqrt((x - centre[0]) ** 2 + (y - centre[1]) ** 2 + (z - centre[2]) ** 2) - radius


def box(half, centre=(0, 0, 0), size=12.0):
    x, y, z = grid(size)
    return np.maximum(
        np.maximum(np.abs(x - centre[0]) - half[0], np.abs(y - centre[1]) - half[1]),
        np.abs(z - centre[2]) - half[2],
    )


class TestInspect:
    def test_a_sphere_has_the_overhang_geometry_says_it_has(self):
        """Everything below 45 degrees of latitude overhangs, (1 - cos45)/2 of the surface,
        less the cap the first layer rests on the plate with: one voxel tall, VOXEL / 2r."""
        report = inspect(ball(), spacing=(VOXEL,) * 3, min_wall=1.0)
        expected = (1 - np.cos(np.radians(45))) / 2 - VOXEL / (2 * 6.0)
        assert report.overhang == pytest.approx(expected, abs=0.02)

    def test_a_cube_has_no_overhang_and_no_islands(self):
        report = inspect(box((5, 5, 5)), spacing=(VOXEL,) * 3, min_wall=1.0)
        assert report.overhang < 0.02      # its underside rests on the plate
        assert report.islands == 0
        assert report.pieces == 1
        assert report.ok

    def test_the_face_on_the_plate_is_not_an_overhang(self):
        """A flat slab: the whole underside faces down, and all of it rests on the plate."""
        report = inspect(box((8, 8, 2)), spacing=(VOXEL,) * 3, min_wall=1.0)
        assert report.overhang < 0.02

    def test_a_ceiling_above_the_plate_still_overhangs(self):
        """The same slab lifted on a post: now its underside is a ceiling."""
        lifted = np.minimum(box((8, 8, 2), (0, 0, 6)), box((1, 1, 4), (0, 0, 0)))
        assert inspect(lifted, spacing=(VOXEL,) * 3, min_wall=1.0).overhang > 0.25

    def test_the_bottom_layer_is_the_build_plate_not_an_island(self):
        """A model resting on the plate has not started in mid-air."""
        assert inspect(ball(), spacing=(VOXEL,) * 3, min_wall=1.0).islands == 0

    def test_a_table_starts_its_top_in_mid_air(self):
        """Two legs and a top: the top appears with nothing under most of it."""
        legs = np.minimum(box((1, 1, 5), (-4, 0, -5)), box((1, 1, 5), (4, 0, -5)))
        top = box((6, 2, 1), (0, 0, 1))
        report = inspect(np.minimum(legs, top), spacing=(VOXEL,) * 3, min_wall=1.0)
        assert report.islands >= 1
        assert report.island_area > 0
        assert not report.ok

    def test_separate_solids_are_counted(self):
        pair = np.minimum(ball(3, (-6, 0, 0)), ball(3, (6, 0, 0)))
        report = inspect(pair, spacing=(VOXEL,) * 3, min_wall=1.0)
        assert report.pieces == 2
        assert report.loose == pytest.approx(0.5, abs=0.05)
        assert "separate pieces" in " ".join(report.problems)

    def test_a_hollow_sphere_traps_its_own_volume(self):
        hollow = np.maximum(ball(6.0), -ball(4.0))
        report = inspect(hollow, spacing=(VOXEL,) * 3, min_wall=1.0)
        assert report.trapped_voids == 1
        assert report.trapped_volume == pytest.approx(4 / 3 * np.pi * 4.0**3 / 1000, rel=0.1)
        assert report.typical == pytest.approx(2.0, rel=0.15)      # a 2 mm wall

    def test_an_open_cavity_is_not_trapped(self):
        """A cavity with a way out is fine; only sealed ones are a problem."""
        x, y, z = grid()
        vented = np.maximum(np.maximum(ball(6.0), -ball(4.0)), -(np.sqrt(x**2 + y**2) - 1.0))
        assert inspect(vented, spacing=(VOXEL,) * 3, min_wall=1.0).trapped_voids == 0

    def test_thin_walls_are_measured_not_guessed(self):
        thin = box((8, 8, 0.6))       # a 1.2 mm plate
        report = inspect(thin, spacing=(VOXEL,) * 3, min_wall=2.0)
        assert report.typical == pytest.approx(1.2, abs=0.3)
        assert report.thin_share > 0.9

    def test_normals_point_out_of_the_solid(self):
        values = ball()
        nx, ny, nz = surface_normals(values, (VOXEL,) * 3)
        skin = np.abs(values) < VOXEL
        x, y, z = grid()
        radial = np.broadcast_to(z, values.shape)[skin] / 6.0
        assert np.corrcoef(nz[skin], radial)[0, 1] > 0.99

    def test_an_empty_field_says_so(self):
        with pytest.raises(ValueError, match="no solid"):
            inspect(np.ones((8, 8, 8)), spacing=(1, 1, 1))

    def test_a_report_reads_as_a_verdict(self, capsys):
        inspect(ball(), spacing=(VOXEL,) * 3, min_wall=1.0).summary()
        printed = capsys.readouterr().out
        assert "verdict" in printed and "wall thickness" in printed


class TestRepairs:
    def test_keeping_the_largest_leaves_one_piece(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import keep_largest

        pair = np.minimum(ball(5, (-6, 0, 0)), ball(2, (7, 0, 0)))
        fixed, what = keep_largest(pair, spacing=(VOXEL,) * 3)
        assert what["pieces_removed"] == 1
        assert inspect(fixed, min_wall=1.0).pieces == 1

    def test_keeping_the_largest_reports_what_it_threw_away(self):
        """The share removed is the number that says whether this is a fix."""
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import keep_largest

        halves = np.minimum(ball(4, (-5, 0, 0)), ball(4, (5, 0, 0)))
        _, what = keep_largest(halves, spacing=(VOXEL,) * 3)
        assert what["material_removed"] == pytest.approx(0.5, abs=0.05)

    def test_draining_opens_a_sealed_cavity(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import drain_voids

        hollow = np.maximum(ball(6.0), -ball(4.0))
        drained, what = drain_voids(hollow, spacing=(VOXEL,) * 3, radius=1.0)
        assert what["drained"] == 1
        assert inspect(drained, min_wall=1.0).trapped_voids == 0

    def test_draining_does_nothing_when_there_is_nothing_to_drain(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import drain_voids

        _, what = drain_voids(ball(), spacing=(VOXEL,) * 3)
        assert what["drained"] == 0

    def test_supporting_removes_the_mid_air_starts(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import make_self_supporting

        legs = np.minimum(box((1, 1, 5), (-4, 0, -5)), box((1, 1, 5), (4, 0, -5)))
        table = np.minimum(legs, box((6, 2, 1), (0, 0, 1)))
        assert inspect(table, spacing=(VOXEL,) * 3, min_wall=1.0).islands >= 1

        braced, what = make_self_supporting(table, spacing=(VOXEL,) * 3, angle=45.0)
        assert inspect(braced, min_wall=1.0).islands == 0
        assert what["material_added"] > 0

    def test_supporting_adds_nothing_to_a_shape_that_stands_up_already(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import make_self_supporting

        _, what = make_self_supporting(box((5, 5, 5)), spacing=(VOXEL,) * 3)
        assert what["material_added"] == pytest.approx(0.0, abs=0.02)

    def test_the_build_direction_is_stated_not_assumed(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import make_self_supporting

        with pytest.raises(ValueError, match="Z build direction"):
            make_self_supporting(box((5, 5, 5)), spacing=(VOXEL,) * 3, direction="x")


class TestUnsupported:
    """The measure the self-supporting fix is accountable to.

    Overhang area does not go to zero when a model is made self-supporting,
    because the buttresses stand at exactly the limit angle. Unsupported area
    does, and it is the thing that actually stops a print.
    """

    @staticmethod
    def cantilever():
        """A column with an arm reaching 16 mm out from it."""
        return np.minimum(box((2, 2, 6), (0, 0, -6)), box((10, 4, 1), (8, 0, 1)))

    def test_a_cantilever_reaches_past_what_holds_it(self):
        report = inspect(self.cantilever(), spacing=(VOXEL,) * 3, min_wall=1.0)
        assert report.unsupported > 1.0
        assert "reaches past" in " ".join(report.problems)

    def test_a_cone_standing_on_its_base_is_supported_all_the_way_up(self):
        x, y, z = grid()
        cone = np.maximum(np.sqrt(x**2 + y**2) - (6.0 - 0.6 * (z + 8)), np.abs(z + 4) - 4)
        assert inspect(cone, spacing=(VOXEL,) * 3, min_wall=1.0).unsupported == pytest.approx(0.0, abs=0.5)

    def test_the_fix_drives_it_to_zero(self):
        pytest.importorskip("skfmm")
        from compas_vol.fabrication import make_self_supporting

        cantilever = self.cantilever()
        assert inspect(cantilever, spacing=(VOXEL,) * 3, min_wall=1.0).unsupported > 1.0

        braced, _ = make_self_supporting(cantilever, spacing=(VOXEL,) * 3, angle=45.0)
        assert inspect(braced, min_wall=1.0).unsupported == pytest.approx(0.0, abs=0.5)
