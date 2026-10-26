"""Cutting one field into pieces that can each be made and computed alone."""

import numpy as np
from compas.geometry import Box, Frame

from compas_vol.combinations import Intersection
from compas_vol.combinations import Subtraction
from compas_vol.combinations import Union
from compas_vol.meshing import normalize_bounds
from compas_vol.primitives import VolBox

__all__ = ["Piece", "Assembly", "Seams", "segment"]

#: Axis names, for piece names and manifests.
_AXES = ("x", "y", "z")


class Piece:
    """One manufacturable part of a segmented model.

    A piece is the whole model intersected with its own box, plus whatever
    registration features its joints add. It is an ordinary volumetric object,
    so everything in the package applies to it -- sample it, inspect it,
    export it, put it in a viewer -- and nothing needs to know it is part of
    something larger.

    Attributes
    ----------
    index : tuple[int, int, int]
        Where it sits in the grid of pieces, or ``(n, 0, 0)`` for the n-th of
        a list of cells.
    name : str
        ``"p_i_j_k"`` unless the cell was given one; stable across runs, and
        usable as a filename.
    role : str | None
        What the piece is in the construction -- ``"node"``, ``"beam"``,
        ``"panel"`` -- when the cells say so.
    bounds : tuple[float, ...]
        ``(xmin, ymin, zmin, xmax, ymax, zmax)`` of this piece's own box,
        already inset by any clearance. Sampling anything larger is wasted
        work: the piece is empty outside it.
    solid : :class:`compas_vol.base.VolObject`
        The piece itself.
    model : :class:`compas_vol.base.VolObject` | None
        The whole model the piece was cut from, which a process run on the
        piece (:meth:`bake`) samples beyond the piece's own box.
    features : list[tuple[str, :class:`compas_vol.base.VolObject`]]
        What the joints added (``"add"``) and took away (``"remove"``), kept
        apart from ``solid`` so they can be applied again after a process --
        a pin is machined, not weathered.
    joints : list[dict]
        One entry per registration feature, saying which axis it crosses,
        whether this piece carries the pin or the socket, and where it is.
    """

    def __init__(self, index, bounds, solid, joints=None, name=None, role=None, model=None):
        self.index = tuple(int(v) for v in index)
        self.bounds = tuple(float(v) for v in bounds)
        self.solid = solid
        self.joints = list(joints or [])
        self.role = role
        self.model = model
        self.features = []
        self.reach = 0.0
        self._name = name

    @property
    def name(self):
        """str: A stable name, usable as a filename."""
        return self._name or "p_{:02d}_{:02d}_{:02d}".format(*self.index)

    def add(self, obj, reach=0.0):
        """Add material to the piece -- a pin -- and remember it as a feature.

        Parameters
        ----------
        obj : :class:`compas_vol.base.VolObject`
        reach : float
            How far it stands proud of the piece's box, so that sampling the
            finished piece goes far enough to close its surface.
        """
        self.solid = Union(self.solid, obj)
        self.features.append(("add", obj))
        self.reach = max(self.reach, float(reach))

    def remove(self, obj):
        """Take material out of the piece -- a socket -- and remember it as a feature."""
        self.solid = Subtraction(self.solid, obj)
        self.features.append(("remove", obj))

    @property
    def size(self):
        """tuple[float, float, float]: The piece box, in model units."""
        return tuple(self.bounds[i + 3] - self.bounds[i] for i in range(3))

    def sample(self, resolution=128, workers=None, redistanced=False):
        """Sample just this piece, over just its own box.

        Parameters
        ----------
        resolution : int | tuple[int, int, int]
            Samples along each axis of *this piece*, not of the model.
        workers : int, optional
        redistanced : bool
            Rebuild the distance field after sampling. Needed before measuring
            a wall thickness, or before any process; not needed to mesh.

        Returns
        -------
        :class:`compas_vol.processes.Field`
        """
        from compas_vol.processes import Field

        return Field.from_object(self.solid, self.bounds, resolution, workers=workers, redistanced=redistanced)

    def process_field(self, process=None, voxel=10.0, halo=0.0, workers=None):
        """Run a process on this piece and the margin around it, before any cut.

        A process -- erosion, pitting -- reads the surface around each point,
        so run on the piece's own box it would see a wall where the cut is
        and wear the piece's edges as if they were the outside of the model.
        Running it over the box grown by ``halo`` lets it see the neighbours'
        material instead; the result is cut back to the piece by :meth:`bake`.

        Sampling is on a world lattice of spacing ``voxel``
        (:meth:`compas_vol.processes.Field.from_object`), so two neighbours'
        halos share their samples exactly where they overlap, and the same
        process sees the same input there. Noise in the processes is defined
        in world coordinates for the same reason.

        Parameters
        ----------
        process : callable, optional
            ``process(field) -> field``. ``None`` just samples.
        voxel : float
            Sample spacing, in model units, the same for every piece.
        halo : float
            How far beyond the piece to sample and process, in model units.
            Make it larger than the longest length the process measures with
            -- a curvature length, a shelter reach -- or the seams will show.
        workers : int, optional
            Sampling threads.

        Returns
        -------
        :class:`compas_vol.processes.Field`
            Over the piece's box grown by ``halo``, on the lattice.
        """
        from compas_vol.processes import Field

        if self.model is None:
            raise ValueError("{} has no model to sample beyond its own box.".format(self.name))
        field = Field.from_object(self.model, _grown(self.bounds, halo), workers=workers, voxel=voxel)
        return process(field) if process is not None else field

    def bake(self, process=None, voxel=10.0, halo=0.0, workers=None, field=None):
        """The finished piece, as a sampled field: processed, cut to its box, jointed.

        Parameters
        ----------
        process, voxel, halo, workers
            As for :meth:`process_field`.
        field : :class:`compas_vol.processes.Field`, optional
            A result of :meth:`process_field` to finish, instead of running
            it again -- for when the raw field is wanted too, to compare
            neighbours across a seam.

        Returns
        -------
        :class:`compas_vol.processes.Field`
            Over the piece's box, plus anything its joints add beyond it,
            plus two voxels, so the surface closes inside the grid and meshes
            watertight.
        """
        from compas_vol.processes import Field

        raw = field if field is not None else self.process_field(process, voxel, halo, workers)
        solid = Intersection(raw.to_volume(), _box(self.bounds))
        for operation, obj in self.features:
            solid = Union(solid, obj) if operation == "add" else Subtraction(solid, obj)
        spacing = min(raw.spacing)
        return Field.from_object(
            solid, _grown(self.bounds, self.reach + 2 * spacing), workers=workers, redistanced=False, voxel=spacing
        )

    def export_stl(self, filepath, resolution=128, workers=None, field=None):
        """Write this piece as a binary STL, closed at its cut faces.

        Parameters
        ----------
        filepath : str
        resolution : int
            Samples along the piece's longest side. Ignored with ``field``.
        workers : int, optional
        field : :class:`compas_vol.processes.Field`, optional
            A baked piece (:meth:`bake`) to write as it is.

        Returns
        -------
        str
            The path written.
        """
        from compas_vol.meshing import iso_surface
        from compas_vol.meshing import sample
        from compas_vol.meshing import write_stl

        if field is None:
            # Sample a little beyond the box: the piece fills it to the cut
            # faces, and a surface that reaches the edge of the grid is left
            # open there.
            voxel = max(self.size) / (int(resolution) - 1)
            grown = _grown(self.bounds, self.reach + 2 * voxel)
            counts = tuple(max(2, int(round((grown[i + 3] - grown[i]) / voxel)) + 1) for i in range(3))
            values, origin, spacing = sample(self.solid, grown, counts, workers=workers)
        else:
            values, origin, spacing = field.values, field.origin, field.spacing
        vertices, faces = iso_surface(values, origin, spacing)
        return write_stl(filepath, vertices, faces, name=self.name)

    def __repr__(self):
        return "Piece({}, {:.0f} x {:.0f} x {:.0f}, {} joint(s))".format(
            self.name, *self.size, len(self.joints)
        )


class Assembly:
    """A model cut into pieces, and the record of how they go back together.

    Iterate it to get :class:`Piece` objects. Nothing is sampled until you ask
    for it, so building the assembly of a whole pavilion costs almost nothing
    -- it is the pieces that cost, and only the ones you build.

    Attributes
    ----------
    pieces : list[:class:`Piece`]
    shape : tuple[int, int, int] | None
        How many pieces along each axis, for a grid; ``None`` for pieces cut
        from a list of cells.
    bounds : tuple[float, ...]
        The whole model's bounds.
    clearance : float
        The gap left between neighbours, in model units.
    interfaces : list[dict]
        Every face two pieces share: ``low`` and ``high`` (the pieces below
        and above it), ``axis``, ``position`` along that axis, and ``rect``,
        the shared rectangle as ``(lo_a, lo_b, hi_a, hi_b)`` over the other
        two axes in order.
    """

    def __init__(self, pieces, shape, bounds, clearance=0.0, interfaces=None):
        self.pieces = list(pieces)
        self.shape = None if shape is None else tuple(int(v) for v in shape)
        self.bounds = tuple(float(v) for v in bounds)
        self.clearance = float(clearance)
        self.interfaces = list(interfaces or [])

    def __len__(self):
        return len(self.pieces)

    def __iter__(self):
        return iter(self.pieces)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            return self._by_index[key]
        return self.pieces[key]

    @property
    def _by_index(self):
        return {piece.index: piece for piece in self.pieces}

    def find(self, name):
        """The piece with this name."""
        for piece in self.pieces:
            if piece.name == name:
                return piece
        raise KeyError(name)

    @property
    def piece_size(self):
        """tuple[float, float, float]: The largest piece box in the assembly."""
        return tuple(max(piece.size[i] for piece in self.pieces) for i in range(3))

    def neighbours(self, piece):
        """The pieces sharing a face with this one.

        Returns
        -------
        list[tuple[int, :class:`Piece`]]
            The axis crossed, and the piece on the other side.
        """
        found = []
        for face in self.interfaces:
            if face["low"] is piece:
                found.append((face["axis"], face["high"]))
            elif face["high"] is piece:
                found.append((face["axis"], face["low"]))
        return sorted(found, key=lambda row: (row[0], row[1].bounds[row[0]]))

    def cost(self, resolution=128, voxel=None, halo=0.0):
        """What it would take to build every piece at this resolution.

        The number that justifies segmenting at all. Sampling the whole model
        at the same voxel size is quoted beside it, because that is the
        alternative and it is usually not possible at any price.

        Parameters
        ----------
        resolution : int
            Samples along each axis of one piece.
        voxel : float, optional
            Quote at this voxel size instead, the way :meth:`build` samples:
            ``per_piece`` is then the largest piece, which is what memory has
            to hold.
        halo : float
            Margin a process samples beyond each piece (and beyond the model).

        Returns
        -------
        dict
            ``voxel`` size in model units, ``per_piece`` and ``whole_model``
            voxel counts, their sizes in bytes as float64, and ``pieces``.

        Examples
        --------
        >>> from compas.geometry import Box
        >>> from compas_vol.primitives import VolBox
        >>> assembly = segment(VolBox(Box(1000.0, 1000.0, 100.0), 0.0), (-500, -500, -50, 500, 500, 50), piece=250.0)
        >>> cost = assembly.cost(voxel=10.0, halo=20.0)
        >>> cost["pieces"], cost["per_piece"], cost["whole_model"]
        (16, 13500, 165375)
        """
        if voxel is not None:
            def count(extent):
                return int(np.prod([np.ceil((e + 2 * halo) / voxel) + 1 for e in extent]))

            per_piece = max(count(piece.size) for piece in self.pieces)
            whole = count(self._extent)
            return {
                "voxel": float(voxel),
                "pieces": len(self.pieces),
                "per_piece": per_piece,
                "per_piece_bytes": per_piece * 8,
                "whole_model": whole,
                "whole_model_bytes": whole * 8,
            }
        voxel = max(self.piece_size) / (resolution - 1)
        per_piece = resolution ** 3
        whole = int(np.prod([extent / voxel + 1 for extent in self._extent]))
        return {
            "voxel": voxel,
            "pieces": len(self.pieces),
            "per_piece": per_piece,
            "per_piece_bytes": per_piece * 8,
            "whole_model": whole,
            "whole_model_bytes": whole * 8,
        }

    @property
    def _extent(self):
        return tuple(self.bounds[i + 3] - self.bounds[i] for i in range(3))

    def build(self, process=None, voxel=10.0, halo=0.0, pieces=None, workers=None, seams=None):
        """Build pieces one at a time: process each with its halo, then finish it.

        A generator, so only one piece is ever in memory: the whole point of
        cutting the model up. Each piece goes through
        :meth:`Piece.process_field` and :meth:`Piece.bake`; give ``seams`` a
        :class:`Seams` to compare neighbours along the way.

        Parameters
        ----------
        process : callable, optional
            ``process(field) -> field``, run on each piece with its halo.
        voxel, halo, workers
            As for :meth:`Piece.process_field`.
        pieces : iterable[:class:`Piece`], optional
            A subset to build. Defaults to every piece.
        seams : :class:`Seams`, optional
            Records each piece's processed field where it meets a neighbour.

        Yields
        ------
        tuple[:class:`Piece`, :class:`compas_vol.processes.Field`, :class:`compas_vol.processes.Field`]
            The piece; its finished field, cut to its box and jointed; and
            the processed field with its halo, before either -- for checks of
            what the process did, which the joints would only confuse.

        Examples
        --------
        >>> from compas.geometry import Box
        >>> from compas_vol.primitives import VolBox
        >>> assembly = segment(VolBox(Box(100.0, 40.0, 40.0), 0.0), (-50, -20, -20, 50, 20, 20), piece=(50, 40, 40))
        >>> [(piece.name, field.shape) for piece, field, _ in assembly.build(voxel=4.0)]
        [('p_00_00_00', (18, 15, 15)), ('p_01_00_00', (18, 15, 15))]
        """
        for piece in (self.pieces if pieces is None else pieces):
            raw = piece.process_field(process, voxel, halo, workers)
            if seams is not None:
                seams.add(piece, raw)
            yield piece, piece.bake(field=raw), raw

    def check(self, resolution=96, **kwargs):
        """Inspect every piece, and say which ones will not build.

        The quality gate of the whole exercise. Two thousand pieces is two
        thousand chances for one to be unmakeable, and finding that out on the
        machine is the expensive way.

        One failure is worth expecting, because it is caused by segmenting
        rather than by the design: **a piece cut from a lattice is usually not
        one part.** Struts that were held together by material outside the
        piece box are cut loose by the box, and drop out. The share of
        material involved is normally tiny -- slivers at the cut face -- but it
        is not nothing, and :func:`compas_vol.fabrication.keep_largest` on each
        piece is the blunt fix. The considered fix is to cut somewhere else.

        Parameters
        ----------
        resolution : int
            Samples along each axis of each piece. Every piece is built, so
            this is the expensive call on an assembly.
        **kwargs
            Passed to :func:`compas_vol.fabrication.inspect` -- ``angle``,
            ``min_wall``, ``density``.

        Returns
        -------
        dict
            ``reports`` keyed by piece name, ``failed`` the names that report
            a problem, and ``loose`` the share of material outside the largest
            piece, worst first.
        """
        from compas_vol.fabrication import inspect

        reports, failed, loose = {}, [], []
        for piece in self.pieces:
            field = piece.sample(resolution, redistanced=True)
            report = inspect(field.values, spacing=field.spacing, origin=field.origin, **kwargs)
            reports[piece.name] = report
            if not report.ok:
                failed.append(piece.name)
            if report.pieces > 1:
                loose.append((piece.name, report.pieces, report.loose))
        loose.sort(key=lambda row: -row[2])
        return {"reports": reports, "failed": failed, "loose": loose}

    def manifest(self, resolution=None):
        """A bill of pieces, as text.

        Parameters
        ----------
        resolution : int, optional
            If given, every piece is sampled at this resolution and its solid
            volume reported. That costs a full build of the assembly, so it is
            off by default.

        Returns
        -------
        str
        """
        layout = "{} x {} x {}".format(*self.shape) if self.shape else "cut from cells"
        lines = [
            "{} pieces, {}".format(len(self.pieces), layout),
            "model    : {:.0f} x {:.0f} x {:.0f} mm".format(*self._extent),
            "piece    : up to {:.0f} x {:.0f} x {:.0f} mm".format(*self.piece_size),
            "clearance: {:.2f} mm between neighbours".format(self.clearance),
            "joints   : {} registration feature(s)".format(sum(len(p.joints) for p in self.pieces) // 2),
            "",
        ]
        width = max([14] + [len(piece.name) + 1 for piece in self.pieces])
        header = "{:<{w}} {:>22} {:>8}".format("piece", "size (mm)", "joints", w=width)
        if resolution:
            header += " {:>12}".format("volume (cm3)")
        lines.append(header)

        for piece in self.pieces:
            row = "{:<{w}} {:>22} {:>8}".format(
                piece.name, "{:.0f} x {:.0f} x {:.0f}".format(*piece.size), len(piece.joints), w=width
            )
            if resolution:
                field = piece.sample(resolution)
                volume = float((field.values < 0).sum()) * float(np.prod(field.spacing)) / 1000.0
                row += " {:>12.1f}".format(volume)
            lines.append(row)
        return "\n".join(lines)

    def __repr__(self):
        if self.shape:
            return "Assembly({} pieces, {}x{}x{})".format(len(self.pieces), *self.shape)
        return "Assembly({} pieces)".format(len(self.pieces))


class Seams:
    """Whether pieces built separately agree where they meet.

    Each piece of a processed model is processed on its own, with a halo, so
    the two sides of a joint are two separate computations. This compares
    them on the face they share, as they are built, keeping only those face
    samples -- never a whole piece -- until the neighbour arrives.

    Two numbers come out per face: how far apart the two surfaces are, read
    only where a surface is near (deep inside the solid, two halos legitimately
    disagree about how far away the far side is, and nothing will ever see
    it), and the share of the face that one side calls solid and the other
    void. A process that respects its halo leaves the first under a voxel and
    the second at zero.

    Parameters
    ----------
    assembly : :class:`Assembly`
    step : float
        Sample spacing on each face; the build voxel is a good choice.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> assembly = segment(VolBox(Box(100.0, 40.0, 40.0), 0.0), (-50, -20, -20, 50, 20, 20), piece=(50, 40, 40))
    >>> seams = Seams(assembly, step=4.0)
    >>> built = list(assembly.build(voxel=4.0, halo=8.0, seams=seams))
    >>> seams.summary()["faces"], seams.summary()["disagreement"]
    (1, 0.0)
    """

    def __init__(self, assembly, step):
        self.assembly = assembly
        self.step = float(step)
        self._waiting = {}
        self.results = []

    def _samples(self, face, grid):
        axis = face["axis"]
        others = [a for a in range(3) if a != axis]
        lo_a, lo_b, hi_a, hi_b = face["rect"]
        coordinates = [None, None, None]
        coordinates[axis] = np.full((1, 1, 1), float(face["position"]))
        for n, (lo, hi) in enumerate(((lo_a, hi_a), (lo_b, hi_b))):
            values = np.arange(lo + self.step / 2, hi, self.step)
            shape = [1, 1, 1]
            shape[others[n]] = len(values)
            coordinates[others[n]] = values.reshape(shape)
        return np.squeeze(grid.get_distance_numpy(*coordinates))

    def add(self, piece, field):
        """Record a piece's processed field (with its halo) on each face it shares."""
        grid = field.to_volume()
        for n, face in enumerate(self.assembly.interfaces):
            if piece is not face["low"] and piece is not face["high"]:
                continue
            values = self._samples(face, grid)
            other = face["high"] if piece is face["low"] else face["low"]
            waiting = self._waiting.pop((n, other.name), None)
            if waiting is None:
                self._waiting[(n, piece.name)] = values
                continue
            near = np.minimum(np.abs(values), np.abs(waiting)) < 2 * self.step
            offset = float(np.abs(values - waiting)[near].max()) if near.any() else 0.0
            disagreement = float(((values < 0) != (waiting < 0)).mean())
            self.results.append({"low": face["low"].name, "high": face["high"].name, "offset": offset,
                                 "disagreement": disagreement})

    def summary(self):
        """The worst face: ``faces`` compared, largest ``offset`` (mm) and ``disagreement`` (share)."""
        return {
            "faces": len(self.results),
            "offset": max((r["offset"] for r in self.results), default=0.0),
            "disagreement": max((r["disagreement"] for r in self.results), default=0.0),
        }


def _edges(low, high, piece):
    """Cut positions along one axis, in pieces no larger than `piece`."""
    extent = high - low
    count = max(1, int(np.ceil(extent / piece - 1e-9)))
    return np.linspace(low, high, count + 1), count


def _grown(bounds, margin):
    """Bounds grown by ``margin`` on every side."""
    margin = float(margin)
    return tuple(v - margin for v in bounds[:3]) + tuple(v + margin for v in bounds[3:])


def _interfaces(cells, tolerance):
    """Every face two cells share, with the rectangle they share it over."""
    found = []
    for a, low in enumerate(cells):
        for b, high in enumerate(cells):
            if a == b:
                continue
            for axis in range(3):
                if abs(low[axis + 3] - high[axis]) > tolerance:
                    continue
                others = [i for i in range(3) if i != axis]
                lo = [max(low[i], high[i]) for i in others]
                hi = [min(low[i + 3], high[i + 3]) for i in others]
                if all(h - v > tolerance for v, h in zip(lo, hi)):
                    found.append({"low": a, "high": b, "axis": axis, "position": low[axis + 3], "rect": tuple(lo + hi)})
    return found


def _box(bounds):
    """A VolBox filling the given bounds."""
    size = [bounds[i + 3] - bounds[i] for i in range(3)]
    centre = [0.5 * (bounds[i] + bounds[i + 3]) for i in range(3)]
    return VolBox(Box(*size, frame=Frame(centre, (1, 0, 0), (0, 1, 0))), 0.0)


def segment(obj, bounds, piece=(200.0, 200.0, 200.0), clearance=0.0, joint=None, resolution=None, cells=None):
    """Cut a model into pieces small enough to make, and to compute.

    Two problems, one cut. A pavilion does not fit on a print bed, a mill bed
    or a lorry; and it does not fit in memory either, which is the one that
    stops the work before it starts. A field has no size, so it costs nothing
    to *describe* a six-metre canopy -- but sampling one at 1 mm voxels is
    6000 cubed, 216 billion samples, 1.7 TB as float64. No machine does that,
    and no amount of patience helps.

    Cut the same canopy into 400 mm pieces and each is 400 cubed at the same
    voxel size: 64 million samples, 512 MB, a couple of minutes. There are 750
    of them, they are independent, and they can be built on different machines
    or on different days. The model is not approximated anywhere: each piece
    evaluates the same field, over a smaller box.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The whole model.
    bounds : :class:`compas.geometry.Box` | float | sequence
        Its extent. See :func:`compas_vol.meshing.normalize_bounds`.
    piece : float | sequence[float]
        The largest piece allowed, per axis, in model units. Pieces come out
        no larger than this and are all equal along each axis, so a 1000 mm
        span at 400 mm gives three pieces of 333 mm, not two of 400 and one
        of 200.
    clearance : float
        Gap left between neighbours, in model units, taken half from each
        side of every internal joint. This is the one number here a fabricator
        will ask for: zero means the pieces are modelled touching, and two
        parts modelled touching do not go together.
    joint : :class:`compas_vol.assembly.Pins`, optional
        Registration features across internal faces. Without one the pieces
        meet on flat cuts and have nothing locating them.
    resolution : int, optional
        Only used when ``joint`` needs to test where material is. Defaults to
        a coarse probe, which is all a pin position needs.
    cells : sequence, optional
        The pieces' boxes, given directly instead of as a grid: each either
        bounds ``(xmin, ymin, zmin, xmax, ymax, zmax)`` or a dict with
        ``bounds`` and optionally ``name`` and ``role``. This is how cuts
        follow the construction rather than a grid -- the faces of beams, a
        panel size, a joint moved off an opening (:func:`place_cuts`).
        ``piece`` is ignored. Cells
        must not overlap; where two touch, that face gets the clearance and
        the joint, wherever it is and however much of it they share.

    Returns
    -------
    :class:`Assembly`

    Notes
    -----
    Pieces are cut on axis-aligned planes. That is the assumption worth
    knowing: a cut along a curved rib is not available. Cells that follow the
    structure along the axes are, and for a slab on a beam grid that is most
    of what a good cut is.

    Examples
    --------
    >>> from compas.geometry import Sphere
    >>> from compas_vol.assembly import segment
    >>> from compas_vol.primitives import VolSphere
    >>> assembly = segment(VolSphere(Sphere(300.0)), bounds=320.0, piece=250.0)
    >>> len(assembly)
    27
    >>> assembly.shape
    (3, 3, 3)
    >>> "{:.0f}".format(assembly.piece_size[0])
    '213'
    """
    x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)

    if cells is None:
        sizes = (piece,) * 3 if isinstance(piece, (int, float)) else tuple(float(v) for v in piece)
        cuts, counts = [], []
        for low, high, allowed in zip((x0, y0, z0), (x1, y1, z1), sizes):
            edges, count = _edges(low, high, allowed)
            cuts.append(edges)
            counts.append(count)
        layout = []
        for i in range(counts[0]):
            for j in range(counts[1]):
                for k in range(counts[2]):
                    index = (i, j, k)
                    box = tuple(cuts[a][n] for a, n in enumerate(index)) + tuple(
                        cuts[a][n + 1] for a, n in enumerate(index)
                    )
                    layout.append({"index": index, "bounds": box})
        shape = counts
    else:
        layout = []
        for n, cell in enumerate(cells):
            cell = cell if isinstance(cell, dict) else {"bounds": cell}
            layout.append(dict(cell, index=(n, 0, 0), bounds=tuple(float(v) for v in cell["bounds"])))
        shape = None

    boxes = [cell["bounds"] for cell in layout]
    extent = max(x1 - x0, y1 - y0, z1 - z0)
    faces = _interfaces(boxes, tolerance=1e-9 * max(extent, 1.0))

    # Clearance is taken off internal faces only: the outside of the assembly
    # is the outside of the model.
    half = 0.5 * float(clearance)
    insets = [[0.0] * 6 for _ in layout]
    for face in faces:
        insets[face["low"]][face["axis"] + 3] = half
        insets[face["high"]][face["axis"]] = half

    pieces = []
    for cell, inset in zip(layout, insets):
        box = tuple(cell["bounds"][i] + inset[i] for i in range(3)) + tuple(
            cell["bounds"][i + 3] - inset[i + 3] for i in range(3)
        )
        pieces.append(
            Piece(cell["index"], box, Intersection(obj, _box(box)), name=cell.get("name"), role=cell.get("role"),
                  model=obj)
        )

    for face in faces:
        face["low"], face["high"] = pieces[face["low"]], pieces[face["high"]]

    assembly = Assembly(pieces, shape, (x0, y0, z0, x1, y1, z1), clearance, interfaces=faces)

    if joint is not None:
        joint.apply(assembly, obj, resolution=resolution)

    return assembly
