"""Fixing what :func:`compas_vol.fabrication.inspect` finds, where it can be fixed.

Each of these changes the geometry, which is a design decision, not a cleanup:
draining a cavity puts a hole through a wall, and making an overhang
self-supporting adds material that was not drawn. They are offered as
operations to choose, and each reports what it did.

Repairs return a :class:`compas_vol.processes.Field`, so they need the
``processes`` extra for redistancing.
"""

import numpy as np

from compas_vol.runtime import require

from ._grid import face_connectivity
from ._grid import largest_piece
from ._grid import unpack

__all__ = ["keep_largest", "drain_voids", "make_self_supporting"]


def _as_field(solid, spacing=None, origin=None):
    """A :class:`compas_vol.processes.Field`, whatever was handed in."""
    from compas_vol.processes import Field

    if isinstance(solid, Field):
        return solid
    values, spacing, origin = unpack(solid, spacing, origin)
    return Field(values, origin, spacing)


def keep_largest(solid, spacing=None, origin=None):
    """Discard everything but the biggest piece.

    The blunt fix for a model that has come apart, and the right one when the
    strays are cutting debris. When they are not -- when a third of the
    material is in the piece being thrown away -- the parameters are wrong and
    this only hides it, which is why the share removed is reported.

    Returns
    -------
    tuple[:class:`compas_vol.processes.Field`, dict]
        The cleaned field, and what was removed.
    """
    field = _as_field(solid, spacing, origin)
    values, count, removed = largest_piece(field.values)
    if not count:
        return field.copy(values), {"pieces_removed": 0, "material_removed": 0.0}

    cleaned = field.copy(values).redistanced()
    cleaned.record("keep_largest", pieces_removed=count, material_removed=removed)
    return cleaned, {"pieces_removed": count, "material_removed": removed}


def drain_voids(solid, spacing=None, origin=None, radius=2.0, direction=(0, 0, 1)):
    """Open a sealed cavity to the outside by drilling a channel out of it.

    A cavity that cannot drain traps uncured resin or unfused powder, and in
    any process it is material paid for and never seen. The alternatives are
    to fill it, which adds weight, or to vent it, which is what this does: a
    channel of ``radius`` from the cavity to the nearest face of the domain,
    along ``direction``.

    It will cut through whatever stands in the way, because that is what
    draining means. Choose the direction accordingly -- upward for a print
    that will be lifted out, sideways for a facade where a hole overhead would
    let water in.

    Parameters
    ----------
    solid : :class:`compas_vol.processes.Field` | :class:`compas_vol.primitives.VolGrid` | array
    spacing, origin : sequence[float], optional
    radius : float
        Channel radius, in mm. Powder needs more than resin; check the
        process's own guidance.
    direction : sequence[float]
        Which way to drill.

    Returns
    -------
    tuple[:class:`compas_vol.processes.Field`, dict]
        The drained field, and how many cavities were opened.
    """
    ndimage = require("scipy.ndimage")

    field = _as_field(solid, spacing, origin)
    values = field.values.copy()
    inside = values < 0

    labels, count = ndimage.label(~inside, structure=face_connectivity())
    at_border = set(np.unique(np.concatenate([
        labels[0].ravel(), labels[-1].ravel(),
        labels[:, 0].ravel(), labels[:, -1].ravel(),
        labels[:, :, 0].ravel(), labels[:, :, -1].ravel(),
    ])))
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    trapped = [i for i in range(1, count + 1) if i not in at_border and sizes[i]]
    if not trapped:
        return field.copy(values), {"drained": 0, "volume": 0.0}

    axes = field.coordinates()
    heading = np.asarray(direction, dtype=float)
    heading = heading / np.linalg.norm(heading)
    volume = 0.0

    for cavity in trapped:
        voxels = np.argwhere(labels == cavity)
        # Start from the point of the cavity furthest along the drilling
        # direction: the shortest way out, and for `up` the highest point,
        # where a bubble would sit anyway.
        world = np.stack([np.asarray(a).ravel()[voxels[:, i]] for i, a in enumerate(axes)], axis=1)
        start = world[np.argmax(world @ heading)]

        # A half-infinite cylinder from there, outward: distance to the axis,
        # for points beyond the start.
        offsets = [axis - start[i] for i, axis in enumerate(axes)]
        along = sum(o * heading[i] for i, o in enumerate(offsets))
        squared = sum(o * o for o in offsets)
        radial = np.sqrt(np.maximum(squared - along * along, 0.0))
        channel = np.maximum(radial - radius, -along)

        # Carve it: everything inside the channel becomes void.
        values = np.where(channel < 0, np.abs(values) + 1e-3, values)
        volume += float(sizes[cavity]) * float(np.prod(field.spacing)) / 1000.0

    drained = field.copy(values).redistanced()
    drained.record("drain_voids", drained=len(trapped), radius=radius, direction=tuple(map(float, direction)))
    return drained, {"drained": len(trapped), "volume": volume}


def make_self_supporting(solid, spacing=None, origin=None, angle=45.0, direction="z"):
    """Add material under the overhangs until the whole model can print itself.

    Sweeping down from the top, each layer must contain the layer above it,
    eroded by how far a printer can reach outward in one layer -- one layer
    height divided by the tangent of the self-supporting angle. Where it does
    not, the material is added. Overhangs turn into tapered buttresses that
    are part of the object rather than scaffolding to be broken off.

    This *changes the design*: the fix is visible, and on a model with large
    ceilings it is most of the volume. Compare the mass before and after
    before accepting it.

    Parameters
    ----------
    solid : :class:`compas_vol.processes.Field` | :class:`compas_vol.primitives.VolGrid` | array
    spacing, origin : sequence[float], optional
    angle : float
        The steepest overhang the process can hold, in degrees from
        horizontal. Buttresses taper at this angle.
    direction : {"z"}
        Build direction. Only Z for now; rotate the model for anything else.

    Returns
    -------
    tuple[:class:`compas_vol.processes.Field`, dict]
        The supported field, and how much material it added.
    """
    ndimage = require("scipy.ndimage")

    if direction != "z":
        raise ValueError("Only a Z build direction is supported; rotate the model instead.")

    field = _as_field(solid, spacing, origin)
    inside = field.values < 0
    before = int(inside.sum())

    # How far the outline may grow per layer: layer height over tan(angle).
    reach = field.spacing[2] / np.tan(np.radians(angle))
    steps = max(int(round(reach / min(field.spacing[0], field.spacing[1]))), 1)
    footprint = ndimage.generate_binary_structure(2, 1)

    # The model's own lowest layer is the build plate: support grows down to
    # it and stops. Carried past it, the sweep would go on tapering to the
    # floor of the sampled domain and prop the model up on a pyramid.
    occupied = np.where(inside.any(axis=(0, 1)))[0]
    plate = int(occupied[0]) if len(occupied) else 0

    supported = inside.copy()
    for k in range(inside.shape[2] - 1, plate, -1):
        above = supported[:, :, k]
        if not above.any():
            continue
        # The layer below has to hold up what sits on it, minus the overhang
        # the process can manage on its own.
        needed = ndimage.binary_erosion(above, structure=footprint, iterations=steps, border_value=0)
        supported[:, :, k - 1] |= needed

    added = float((supported.sum() - before) / max(before, 1))
    values = np.where(supported, -np.abs(field.values) - 1e-6, np.abs(field.values) + 1e-6)
    result = field.copy(values).redistanced()
    result.record("make_self_supporting", angle=angle, material_added=added)
    return result, {"material_added": added, "angle": angle}
