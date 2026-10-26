"""What is wrong with this solid, before a printer finds out."""

import numpy as np

from compas_vol.runtime import require

from ._grid import face_connectivity
from ._grid import unpack

__all__ = ["inspect", "Report", "surface_normals"]


def surface_normals(values, spacing):
    """Outward unit normals of the surface, from the gradient of the field.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, ...]
        The three components, each the shape of the grid.
    """
    gradients = np.gradient(values, *spacing)
    magnitude = np.maximum(np.sqrt(sum(g * g for g in gradients)), 1e-12)
    return tuple(g / magnitude for g in gradients)


class Report:
    """What :func:`inspect` found, as numbers and as a verdict.

    Attributes
    ----------
    pieces : int
        Separate solids. More than one and the model is not a part.
    loose : float
        Share of the material outside the largest piece.
    trapped_voids : int
        Cavities sealed off from the outside. Air pockets in FDM; in resin or
        powder they hold uncured material that cannot drain.
    trapped_volume : float
        Their total volume, in cm3.
    overhang : float
        Share of the surface steeper than the threshold angle, leaving out the
        face that rests on the build plate.
    islands : int
        Layers that start in mid-air: regions with nothing beneath them to
        print onto. Unlike a general overhang, these cannot be bridged.
    island_area : float
        Their footprint, in cm2.
    unsupported : float
        Area, in cm2, that reaches further out than the layer below it can
        hold at the threshold angle. This is what
        :func:`compas_vol.fabrication.make_self_supporting` drives to zero.
        The overhang figure does not go to zero even then, because the
        buttresses it adds stand at exactly the limit angle.
    thinnest, typical : float
        Wall thickness, in mm. ``thinnest`` is the 1st percentile, which is
        what the thin features actually measure rather than the single worst
        voxel.
    thin_share : float
        Share of the walls below ``min_wall``.
    volume : float
        Solid volume, in cm3.
    size : tuple[float, float, float]
        Bounding box, in mm.
    """

    def __init__(self, **found):
        self.__dict__.update(found)

    @property
    def problems(self):
        """list[str]: What would stop this printing, in the order it matters."""
        trouble = []
        if self.pieces > 1:
            trouble.append("{} separate pieces ({:.1%} of the material is loose)".format(self.pieces, self.loose))
        if self.trapped_voids:
            trouble.append("{} sealed cavities holding {:.1f} cm3".format(self.trapped_voids, self.trapped_volume))
        if self.islands:
            trouble.append("{} regions start in mid-air ({:.1f} cm2)".format(self.islands, self.island_area))
        if self.unsupported > 0.5:
            trouble.append("{:.1f} cm2 reaches past what the layer below can hold".format(self.unsupported))
        if self.thin_share > 0.01:
            trouble.append("{:.1%} of the walls are under {:.1f} mm".format(self.thin_share, self.min_wall))
        if self.overhang > 0.25:
            trouble.append("{:.0%} of the surface overhangs past {:.0f} degrees".format(self.overhang, self.angle))
        return trouble

    @property
    def ok(self):
        """bool: Nothing found that would stop it printing."""
        return not self.problems

    def __str__(self):
        """str: The findings and what to do about them, as text.

        Separate from :meth:`summary` because not every context has a console
        to print to: a Grasshopper panel and a log file both want the string.
        """
        lines = [
            "size           : {:.1f} x {:.1f} x {:.1f} mm, {:.0f} cm3".format(*self.size, self.volume),
            "pieces         : {}{}".format(self.pieces, "" if self.pieces == 1 else "  <- not one part"),
            "sealed cavities: {}{}".format(
                self.trapped_voids,
                "" if not self.trapped_voids else "  ({:.1f} cm3 trapped)".format(self.trapped_volume),
            ),
            "overhang       : {:.0%} of the surface past {:.0f} degrees".format(self.overhang, self.angle),
            "mid-air starts : {} regions, {:.1f} cm2".format(self.islands, self.island_area),
            "unsupported    : {:.1f} cm2 reaching past the layer below".format(self.unsupported),
            "wall thickness : {:.1f} mm typical, {:.1f} mm thinnest, {:.1%} under {:.1f} mm".format(
                self.typical, self.thinnest, self.thin_share, self.min_wall
            ),
        ]
        if self.ok:
            lines.append("verdict        : ready")
        else:
            lines.append("verdict        : {} problem(s)".format(len(self.problems)))
            lines.extend("  - {}".format(problem) for problem in self.problems)
            lines.append("  fixes: compas_vol.fabrication.keep_largest, drain_voids, make_self_supporting,")
            lines.append("         compas_vol.processes.opened")
        return "\n".join(lines)

    def summary(self):
        """Print the findings, and return the report so calls can be chained."""
        print(self)
        return self

    def __repr__(self):
        return "Report({} piece(s), {} cavities, {:.0%} overhang, {})".format(
            self.pieces, self.trapped_voids, self.overhang, "ok" if self.ok else "problems"
        )


def inspect(solid, spacing=None, origin=None, angle=45.0, min_wall=1.6, density=1.24):
    """Check a sampled solid for the things that stop a model printing.

    Everything is measured on the grid the solid was sampled on, which is
    also where the fixes work, so a problem found here can be handed straight
    to :mod:`compas_vol.fabrication` without meshing anything.

    Parameters
    ----------
    solid : :class:`compas_vol.processes.Field` | :class:`compas_vol.primitives.VolGrid` | array
        A sampled distance field, negative inside. Wall thickness is read
        from the values, so pass a *metric* field -- one that has been
        redistanced, as :meth:`compas_vol.processes.Field.from_object` does.
        On a raw TPMS or a blended tree the thicknesses will be wrong.
    spacing, origin : sequence[float], optional
        Needed only when passing a bare array.
    angle : float
        Overhang threshold in degrees from horizontal. 45 is the usual rule
        for fused deposition.
    min_wall : float
        The thinnest wall the process can hold, in mm.
    density : float
        For the mass estimate, in g/cm3. Default is PLA.

    Returns
    -------
    :class:`Report`

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.fabrication import inspect
    >>> x, y, z = np.ogrid[-10:10:41j, -10:10:41j, -10:10:41j]
    >>> ball = np.sqrt(x**2 + y**2 + z**2) - 6.0
    >>> report = inspect(ball, spacing=(0.5, 0.5, 0.5), min_wall=1.0)
    >>> report.pieces, report.trapped_voids
    (1, 0)
    """
    ndimage = require("scipy.ndimage")

    values, spacing, origin = unpack(solid, spacing, origin)
    voxel = float(np.prod(spacing))
    inside = values < 0
    if not inside.any():
        raise ValueError("There is no solid in this field: every value is positive.")

    # -- pieces
    labels, pieces = ndimage.label(inside, structure=face_connectivity())
    sizes = np.bincount(labels.ravel())[1:]
    loose = float(1 - sizes.max() / sizes.sum()) if pieces > 1 else 0.0

    # -- cavities that cannot drain: void not connected to the outside world
    void_labels, void_count = ndimage.label(~inside, structure=face_connectivity())
    at_border = set(np.unique(np.concatenate([
        void_labels[0].ravel(), void_labels[-1].ravel(),
        void_labels[:, 0].ravel(), void_labels[:, -1].ravel(),
        void_labels[:, :, 0].ravel(), void_labels[:, :, -1].ravel(),
    ])))
    void_sizes = np.bincount(void_labels.ravel(), minlength=void_count + 1)
    trapped = [i for i in range(1, void_count + 1) if i not in at_border and void_sizes[i]]
    trapped_volume = float(sum(void_sizes[i] for i in trapped)) * voxel / 1000.0

    # The lowest layer of the model sits on the build plate: it is supported
    # by definition, and its underside is the contact with the plate.
    occupied = np.where(inside.any(axis=(0, 1)))[0]
    first = int(occupied[0]) if len(occupied) else inside.shape[2]

    # -- overhang, from the surface normal. A vertical wall has nz = 0; a
    #    ceiling has nz = -1. The threshold is the sine of the angle. The face
    #    resting on the plate is left out: the skin over the first layer's
    #    footprint, a voxel either side. A sphere touches the plate at a point,
    #    so its underside still counts; a slab's underside does not.
    skin = np.abs(values) < min(spacing)
    if first < inside.shape[2]:
        lo, hi = max(first - 1, 0), min(first + 1, inside.shape[2])
        footprint = ndimage.binary_dilation(inside[:, :, first])   # and its edge
        skin[:, :, lo:hi] &= ~footprint[:, :, None]
    _, _, nz = surface_normals(values, spacing)
    steep = nz[skin] < -np.sin(np.radians(angle))
    overhang = float(steep.mean()) if skin.any() else 0.0

    # -- islands: cross-sections that appear with nothing underneath them.
    #    A printer can bridge a gap, but it cannot start a layer in mid-air.
    islands, island_voxels = 0, 0
    previous = inside[:, :, first] if first < inside.shape[2] else np.zeros(inside.shape[:2], dtype=bool)
    for k in range(first + 1, inside.shape[2]):
        layer = inside[:, :, k]
        if not layer.any():
            previous = layer
            continue
        regions, count = ndimage.label(layer)
        if count:
            supported = set(np.unique(regions[previous & layer]))
            for region in range(1, count + 1):
                if region not in supported:
                    islands += 1
                    island_voxels += int((regions == region).sum())
        previous = layer
    island_area = island_voxels * spacing[0] * spacing[1] / 100.0

    # -- unsupported area: material that overhangs the layer below by more
    #    than the process can reach outward in one layer.
    reach = spacing[2] / np.tan(np.radians(angle))
    steps = max(int(round(reach / min(spacing[0], spacing[1]))), 1)
    neighbourhood = ndimage.generate_binary_structure(2, 1)
    unsupported_voxels = 0
    for k in range(first + 1, inside.shape[2]):
        layer = inside[:, :, k]
        if not layer.any():
            continue
        held = ndimage.binary_dilation(inside[:, :, k - 1], structure=neighbourhood, iterations=steps)
        unsupported_voxels += int((layer & ~held).sum())
    unsupported = unsupported_voxels * spacing[0] * spacing[1] / 100.0

    # -- wall thickness, read from the field rather than from the voxels.
    #    Inside a distance field, -phi *is* the distance to the surface, so
    #    the ridge of local maxima running along a wall gives its half
    #    thickness directly and sub-voxel. A distance transform of the
    #    thresholded solid would measure to the centres of the void voxels
    #    instead, which inflates a thin wall by about one voxel: a 1.2 mm
    #    plate reads as 2.0 mm at half-millimetre sampling.
    depth = np.where(inside, -values, 0.0)
    ridge = inside & (depth >= ndimage.maximum_filter(depth, size=3) - 1e-9)
    widths = 2 * depth[ridge] if ridge.any() else np.zeros(1)

    coordinates = np.argwhere(inside)
    size = tuple((coordinates.max(axis=0) - coordinates.min(axis=0) + 1) * np.array(spacing))
    volume = float(inside.sum()) * voxel / 1000.0

    return Report(
        pieces=int(pieces),
        loose=loose,
        trapped_voids=len(trapped),
        trapped_volume=trapped_volume,
        overhang=overhang,
        angle=angle,
        islands=int(islands),
        island_area=float(island_area),
        unsupported=float(unsupported),
        thinnest=float(np.percentile(widths, 1)),
        typical=float(np.median(widths)),
        thin_share=float((widths < min_wall).mean()),
        min_wall=min_wall,
        volume=volume,
        mass=volume * density,
        size=size,
        spacing=spacing,
        origin=origin,
    )
