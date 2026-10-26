"""Registration features across the cuts, so pieces locate each other."""

import numpy as np
from compas.geometry import Cylinder, Frame

from compas_vol.combinations import Union
from compas_vol.primitives import VolCylinder

__all__ = ["Pins"]

#: Frames whose normal points along each axis, for orienting a pin.
_FRAMES = (
    ((0, 1, 0), (0, 0, 1)),   # normal +x
    ((0, 0, 1), (1, 0, 0)),   # normal +y
    ((1, 0, 0), (0, 1, 0)),   # normal +z
)


class Pins:
    """Pin-and-socket registration on every internal cut.

    A flat cut locates nothing. Two pieces that meet on a plane can slide in
    both directions along it and rotate about its normal, so an assembly of
    them is only as accurate as whoever holds them. A pin standing proud of
    one face and a socket sunk into the other take all three away.

    The pin is added to the piece on the low side of the cut and the socket is
    taken out of the piece on the high side, so exactly one of each exists per
    joint and the two are modelled from the same centre line.

    Where the pins go is not a pattern imposed on the face: candidate
    positions are tested against the model, and only the ones with enough
    material around them on both sides are kept. A canopy that is mostly void
    at a given cut gets pins only where its ribs cross it -- which is where
    they would have been drawn anyway.

    Parameters
    ----------
    diameter : float
        Pin diameter, in model units.
    depth : float
        How far the pin stands proud of the cut. The socket is cut to the
        same depth, so the pin is ``2 * depth`` long in total.
    fit : float
        Radial clearance added to the socket, in model units. This is a
        *fit*, not a gap: 0.1 to 0.2 mm for a printed peg, more for anything
        cast or cut.
    spacing : float
        Target distance between candidate positions on a cut face.
    margin : float
        How much material a pin needs around it to be kept, beyond its own
        radius. A pin on a 2 mm wall with no margin is a pin sticking out of
        the edge of a 2 mm wall.
    limit : int
        Most pins per cut face. Three locate a plane; more is usually
        alignment for its own sake.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.assembly import Pins, segment
    >>> from compas_vol.primitives import VolBox
    >>> block = VolBox(Box(300.0, 100.0, 100.0), 0.0)
    >>> assembly = segment(block, bounds=(-160, -60, -60, 160, 60, 60),
    ...                    piece=(110.0, 200.0, 200.0), clearance=0.4,
    ...                    joint=Pins(diameter=8.0, depth=5.0, fit=0.15))
    >>> len(assembly)
    3
    >>> [len(piece.joints) for piece in assembly]
    [3, 6, 3]

    The middle piece carries both halves of both its joints; the two ends
    carry one each.
    """

    def __init__(self, diameter=8.0, depth=5.0, fit=0.15, spacing=60.0, margin=1.0, limit=3):
        self.diameter = float(diameter)
        self.depth = float(depth)
        self.fit = float(fit)
        self.spacing = float(spacing)
        self.margin = float(margin)
        self.limit = int(limit)

    def __repr__(self):
        return "Pins(diameter={}, depth={}, fit={})".format(self.diameter, self.depth, self.fit)

    def _candidates(self, rect, axis, position):
        """A grid of positions on one shared face, ``rect`` over the other two axes."""
        others = [a for a in range(3) if a != axis]
        spans = []
        for n, a in enumerate(others):
            low, high = rect[n], rect[n + 2]
            count = max(1, int(np.floor((high - low) / self.spacing)))
            # Inset by a margin so a candidate is never on the very edge.
            inset = (high - low) / (count + 1)
            spans.append(np.linspace(low + inset, high - inset, count))

        grid = np.stack(np.meshgrid(*spans, indexing="ij"), axis=-1).reshape(-1, 2)
        points = np.zeros((len(grid), 3))
        points[:, axis] = position
        points[:, others[0]] = grid[:, 0]
        points[:, others[1]] = grid[:, 1]
        return points

    def _keep(self, obj, points, axis):
        """Positions with enough material around them, on both sides of the cut.

        The field is read at the cut and a pin-length either side of it. All
        three have to be solid by at least the pin's radius plus the margin,
        or the pin has nothing to grip and the socket breaks out of a wall.
        """
        need = -(0.5 * self.diameter + self.margin)
        offsets = (-self.depth, 0.0, self.depth)
        scores = []
        for point in points:
            worst = 0.0
            for offset in offsets:
                probe = list(point)
                probe[axis] += offset
                worst = min(worst, obj.get_distance(probe))
                if worst > need:
                    break
            scores.append(worst)
        scores = np.asarray(scores)
        good = np.nonzero(scores <= need)[0]
        # The most buried candidates first: they are the safest pins.
        return points[good[np.argsort(scores[good])][: self.limit]]

    def _cylinder(self, centre, axis, radius, height):
        xaxis, yaxis = _FRAMES[axis]
        return VolCylinder(Cylinder(radius, height, frame=Frame(list(centre), xaxis, yaxis)))

    def apply(self, assembly, obj, resolution=None):
        """Add a pin and a socket to every face two pieces share.

        Called by :func:`compas_vol.assembly.segment`; there is rarely a
        reason to call it directly.
        """
        radius = 0.5 * self.diameter
        for face in assembly.interfaces:
            piece, other, axis = face["low"], face["high"], face["axis"]
            # Candidates go on the part of the face both pieces still have
            # after clearance, so a pin never lands on a neighbour's gap.
            others = [a for a in range(3) if a != axis]
            rect = [max(piece.bounds[a], other.bounds[a]) for a in others]
            rect += [min(piece.bounds[a + 3], other.bounds[a + 3]) for a in others]
            position = 0.5 * (piece.bounds[axis + 3] + other.bounds[axis])

            points = self._keep(obj, self._candidates(rect, axis, position), axis)
            if not len(points):
                continue

            pins, sockets = [], []
            for centre in points:
                pins.append(self._cylinder(centre, axis, radius, 2 * self.depth))
                sockets.append(self._cylinder(centre, axis, radius + self.fit, 2 * self.depth))
                record = {"axis": axis, "at": tuple(float(v) for v in centre)}
                piece.joints.append(dict(record, role="pin", with_=other.name))
                other.joints.append(dict(record, role="socket", with_=piece.name))

            piece.add(_combine(pins), reach=self.depth)
            other.remove(_combine(sockets))


def _combine(objects):
    """Union a list of objects, without a redundant wrapper for a single one."""
    combined = objects[0]
    for other in objects[1:]:
        combined = Union(combined, other)
    return combined
