"""
********************************************************************************
compas_vol.nodes
********************************************************************************

.. currentmodule:: compas_vol.nodes

The Grasshopper components, without Grasshopper.

Every component in ``compas_vol/ghpython/components/`` is a thin wrapper of
one function here: ``Cv_Box`` calls :func:`box`, ``Cv_Boolean`` calls
:func:`boolean`, and so on. Each function takes the component's inputs by the
same names, with the same defaults, and returns its outputs in the same order
-- but in COMPAS and NumPy types instead of Rhino ones. The component only
converts on the way in and out (:mod:`compas_vol.ghpython`).

That has two uses. A definition worked out on the canvas can be rewritten as a
plain script, node for node, and run headless: no canvas, no Rhino geometry in
between, sampling on every core, and the final model written with
:func:`compas_vol.meshing.export_stl` at a resolution Grasshopper could not
draw. And everything a component does can be tested here, where pytest runs,
rather than only inside Rhino. ``tests/test_ghpython.py`` checks that every
node's signature still matches its component.

Inputs follow Grasshopper's conventions, because that is where they are wired
up: an input left unconnected arrives as ``None`` and falls back to its
default, and a node whose required input is missing returns ``None`` rather
than raising, the way an unwired component stays empty.

The same model as a canvas of five components::

    >>> from compas.geometry import Point
    >>> from compas_vol import nodes
    >>> ball = nodes.sphere(Point(0, 0, 0), 12.0)
    >>> cube = nodes.box(None, 18.0, None, None, 2.0)
    >>> body = nodes.boolean([cube, ball], "intersection", 1.0)
    >>> body = nodes.boolean([body, nodes.tpms("Gyroid", 6.0, 1.2, None, None)], "intersection", 0)
    >>> vertices, faces = nodes.mesh(body, (-10, -10, -10, 10, 10, 10), 48, 0)  # doctest: +SKIP

.. autosummary::
    :toctree: generated/
    :nosignatures:

    sphere
    box
    cylinder
    tpms
    boolean
    shell
    abrasion
    differential
    pitting
    strata
    runoff
    jointing
    fingering
    accretion
    branching
    spinodal
    reactiondiffusion
    morphology
    mesh
    inspect
    info

The process nodes -- erosion, growth, phase separation -- are simulations on a
sampled grid rather than expressions, and each returns its result as a
:class:`compas_vol.primitives.VolGrid`, so it combines, shells and meshes like
anything else. Handed a grid with no ``bounds``, a process runs on that grid
as it is, which is how processes chain without resampling; and the mesh and
inspect nodes, handed a grid with no ``bounds``, read the domain off it::

    >>> body = nodes.box(None, 60.0, None, None, 0)
    >>> worn, history = nodes.abrasion(body, 45.0, 32, 3.0, None, None)  # doctest: +SKIP
    >>> pitted, history = nodes.pitting(worn, None, None, 4.0, None, None, None, None, 0)  # doctest: +SKIP
    >>> vertices, faces = nodes.mesh(pitted, None, None, 0)  # doctest: +SKIP

"""

__all__ = [
    "sphere",
    "box",
    "cylinder",
    "tpms",
    "boolean",
    "shell",
    "abrasion",
    "differential",
    "pitting",
    "strata",
    "runoff",
    "jointing",
    "fingering",
    "accretion",
    "branching",
    "spinodal",
    "reactiondiffusion",
    "morphology",
    "mesh",
    "inspect",
    "info",
]


def _float(value, default):
    """``value`` as a float, or ``default`` when it is unset.

    Zero counts as unset only where the component says so, by passing the
    default; ``None`` always does.
    """
    return default if value is None else float(value)


def _options(**values):
    """The keyword arguments that were actually given.

    The process functions carry their own defaults, in millimetres, and those
    are the documented ones. Passing only what is wired keeps a single source
    for them instead of a second copy here that could drift.
    """
    return {k: v for k, v in values.items() if v is not None}


def _grid_domain(vol, bounds, resolution):
    """``bounds`` and ``resolution``, read off a grid when they are unwired.

    A :class:`compas_vol.primitives.VolGrid` knows the box it was sampled
    over; sampling it again over that box at its own shape reproduces its
    values exactly, so leaving both unwired costs nothing.
    """
    from compas_vol.primitives import VolGrid

    if bounds is None and isinstance(vol, VolGrid):
        return vol.bounds, resolution or vol.values.shape
    return bounds, resolution


def _field(vol, bounds, resolution):
    """The process field for a component's ``vol``, ``bounds`` and ``resolution``.

    A grid with nothing in ``bounds`` is used as it is -- the output of
    another process, which is already a distance field on the grid it was
    made on, so resampling would only blur it. Anything else is sampled over
    ``bounds``, and without them there is nothing to sample.
    """
    from compas_vol.primitives import VolGrid
    from compas_vol.processes import Field

    if vol is None:
        return None
    if bounds is None:
        if isinstance(vol, VolGrid):
            return vol.to_field()
        return None
    return Field.from_object(vol, bounds, int(resolution or 64))


def _result(field):
    """A process component's outputs: the result as a volume, and how it was made."""
    if field is None:
        return None, None
    return field.to_volume(), field.provenance()


# ==============================================================================
# primitives
# ==============================================================================


def sphere(point, radius):
    """A sphere as a signed distance field.

    Parameters
    ----------
    point : :class:`compas.geometry.Point`, optional
        Centre. Defaults to the world origin.
    radius : float
        Radius, in model units.

    Returns
    -------
    :class:`compas_vol.primitives.VolSphere` | None

    Examples
    --------
    >>> s = sphere(None, 5.0)
    >>> round(s.get_distance([8, 0, 0]), 6)
    3.0
    """
    from compas.geometry import Sphere

    from compas_vol.primitives import VolSphere

    if radius is None:
        return None
    return VolSphere(Sphere(float(radius), point=point))


def box(plane, xsize, ysize, zsize, radius):
    """A box as a signed distance field, with optionally rounded edges.

    Parameters
    ----------
    plane : :class:`compas.geometry.Frame`, optional
        The box's frame, at its centre. Defaults to world XY.
    xsize : float
        Size along the frame's X axis.
    ysize, zsize : float, optional
        Size along Y and Z. Each defaults to ``xsize``.
    radius : float, optional
        Edge fillet radius. ``0`` leaves the edges sharp.

    Returns
    -------
    :class:`compas_vol.primitives.VolBox` | None

    Examples
    --------
    >>> b = box(None, 10.0, None, 4.0, 0)
    >>> round(b.get_distance([0, 0, 5]), 6)
    3.0
    """
    from compas.geometry import Box

    from compas_vol.primitives import VolBox

    if xsize is None:
        return None
    x = float(xsize)
    # 0 is not a size anyone means, so it falls back like an unwired input.
    y = float(ysize) if ysize else x
    z = float(zsize) if zsize else x
    return VolBox(Box(x, y, z, frame=plane), _float(radius, 0.0))


def cylinder(plane, radius, height):
    """A cylinder as a signed distance field.

    Parameters
    ----------
    plane : :class:`compas.geometry.Frame`, optional
        The cylinder's frame, at its mid-height. Defaults to world XY.
    radius : float
        Radius, in model units.
    height : float
        Total height, in model units.

    Returns
    -------
    :class:`compas_vol.primitives.VolCylinder` | None

    Examples
    --------
    >>> c = cylinder(None, 2.0, 10.0)
    >>> round(c.get_distance([5, 0, 0]), 6)
    3.0
    """
    from compas.geometry import Cylinder

    from compas_vol.primitives import VolCylinder

    if radius is None or height is None:
        return None
    return VolCylinder(Cylinder(float(radius), float(height), frame=plane))


# ==============================================================================
# microstructures
# ==============================================================================


def tpms(type, cell, thickness, mode, plane):
    """A triply periodic minimal surface, thickened into a printable solid.

    Parameters
    ----------
    type : str | int, optional
        Surface name or index, as :class:`compas_vol.microstructures.TPMSSolid`
        takes it. Defaults to Gyroid.
    cell : float, optional
        Cell size, the true period of the pattern. Defaults to 10.
    thickness : float, optional
        Wall thickness, in model units. Defaults to 1.
    mode : str, optional
        ``"sheet"`` or ``"network"``. Defaults to sheet.
    plane : :class:`compas.geometry.Frame`, optional
        Orients and positions the lattice. Defaults to world XY.

    Returns
    -------
    :class:`compas_vol.microstructures.TPMSSolid`

    Examples
    --------
    >>> t = tpms(None, None, None, None, None)
    >>> (t.tpmstype, t.cell_size, t.thickness, t.mode)
    (0, 10.0, 1.0, 'sheet')
    """
    from compas_vol.microstructures import TPMSSolid

    return TPMSSolid(
        tpmstype=0 if type is None else type,
        cell_size=float(cell) if cell else 10.0,
        thickness=float(thickness) if thickness else 1.0,
        mode=mode or "sheet",
        frame=plane,
    )


# ==============================================================================
# operations
# ==============================================================================


def boolean(vols, operation, blend):
    """Combine volumetric objects, optionally with a smooth blend at the seam.

    Parameters
    ----------
    vols : list[:class:`compas_vol.base.VolObject`]
        Two or more objects. ``None`` entries are dropped, as Grasshopper
        hands over a list with holes in it.
    operation : str, optional
        ``"union"``, ``"intersection"`` or ``"difference"``. Defaults to union.
        ``"difference"`` subtracts every later object from the first.
    blend : float, optional
        Fillet radius at the seam, in model units. ``0`` is a hard boolean.

    Returns
    -------
    :class:`compas_vol.base.VolObject` | None
        ``None`` for an empty list, the object itself for a list of one.

    Raises
    ------
    ValueError
        For an operation that is not one of the three.

    Examples
    --------
    >>> a, b = sphere(None, 5.0), box(None, 6.0, None, None, 0)
    >>> type(boolean([a, b], "difference", 0)).__name__
    'Subtraction'
    >>> type(boolean([a, b], "Union", 1.5)).__name__
    'SmoothUnion'
    """
    from compas_vol.combinations import Intersection
    from compas_vol.combinations import SmoothIntersection
    from compas_vol.combinations import SmoothSubtraction
    from compas_vol.combinations import SmoothUnion
    from compas_vol.combinations import Subtraction
    from compas_vol.combinations import Union

    vols = [v for v in (vols or []) if v is not None]
    if not vols:
        return None
    if len(vols) == 1:
        return vols[0]

    radius = _float(blend, 0.0)
    name = (operation or "union").strip().lower()
    hard = {"union": Union, "intersection": Intersection, "difference": Subtraction}
    smooth = {"union": SmoothUnion, "intersection": SmoothIntersection, "difference": SmoothSubtraction}
    if name not in hard:
        raise ValueError('operation must be union, intersection or difference; got "{}".'.format(operation))

    # Both forms are binary, so a list folds left. For difference that is the
    # meaning a designer expects: the first object, less all the rest.
    result = vols[0]
    for other in vols[1:]:
        result = smooth[name](result, other, radius) if radius > 0 else hard[name](result, other)
    return result


def shell(vol, thickness):
    """Hollow a volumetric object out into a shell of even thickness.

    The wall is centred on the original surface. ``thickness`` is only in
    model units if the field is metric: primitives and booleans of them are,
    a remapped or multiplied field is not.

    Parameters
    ----------
    vol : :class:`compas_vol.base.VolObject`
        The object to hollow.
    thickness : float, optional
        Wall thickness, in model units. Defaults to 1.

    Returns
    -------
    :class:`compas_vol.modifications.Shell` | None

    Examples
    --------
    >>> s = shell(sphere(None, 5.0), 2.0)
    >>> round(s.get_distance([5, 0, 0]), 6)
    -1.0
    """
    from compas_vol.modifications import Shell

    if vol is None:
        return None
    # side=0.5 centres the wall. Shell's own default (0) puts it all outside.
    return Shell(vol, float(thickness) if thickness else 1.0, side=0.5)


# ==============================================================================
# processes
# ==============================================================================


def abrasion(vol, bounds, resolution, depth, length, edge_bias, run=None):
    """Weathering that rounds: what sticks out wears first.

    Parameters
    ----------
    vol : :class:`compas_vol.base.VolObject`
        The starting solid. A :class:`compas_vol.primitives.VolGrid` with no
        ``bounds`` runs on its own grid.
    bounds : float | sequence, optional
        The box to sample ``vol`` over. Leave room: the surface only retreats
        here, but anything touching the edge is cut there.
    resolution : int, optional
        Samples per axis. Defaults to 64. It sets the finest feature any
        process can make: below about two voxels, nothing survives.
    depth : float, optional
        Millimetres removed from a flat face. Defaults to 4.
    length : float, optional
        Feature size curvature is measured against, roughly the radius the
        sharpest edge ends up with. Defaults to 9.
    edge_bias : float, optional
        How much faster an edge wears than a face. Defaults to 2.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]
        The worn solid, and how it was made.

    See Also
    --------
    :func:`compas_vol.processes.abrasion`

    Examples
    --------
    >>> worn, history = abrasion(box(None, 20.0, None, None, 0), 14.0, 24, 1.0, None, 0)
    >>> round(worn.get_distance([10, 0, 0]), 1)   # a flat face, 1 mm back
    1.0
    >>> history.splitlines()[-1].split("(")[0]
    'abrasion'
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    return _result(processes.abrasion(field, **_options(depth=depth, length=length, edge_bias=edge_bias)))


def differential(vol, bounds, resolution, depth, cell, seed, run=None):
    """Weathering by hardness: soft rock retreats, hard rock stands proud.

    One pass, no iteration, so it is the cheapest of the weathering nodes.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`.
    depth : float, optional
        Millimetres removed where the rock is softest. Defaults to 7.
    cell : float, optional
        Size of the hard and soft patches, in mm. Defaults to 25.
    seed : int, optional
        Which variation of the hardness noise.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.differential`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    options = _options(depth=depth, cell_size=cell, seed=None if seed is None else int(seed))
    return _result(processes.differential(field, **options))


def pitting(vol, bounds, resolution, depth, length, threshold, feedback, cell, seed, run=None):
    """Weathering into hollows that deepen themselves: tafoni, honeycombing.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`.
    depth : float, optional
        Millimetres removed at the weakest, deepest point. Defaults to 9.
    length : float, optional
        Roughly the width of a pit, in mm. Defaults to 6.
    threshold : float, optional
        Hardness, in ``[-1, 1]``, above which nothing pits. Raise it for fewer,
        more separate hollows. Defaults to 0.2.
    feedback : float, optional
        How much a hollow speeds its own deepening. Defaults to 1.7.
    cell : float, optional
        Size of the weak patches pits start in, in mm. Defaults to 25.
    seed : int, optional
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.pitting`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    options = _options(
        depth=depth, length=length, threshold=threshold, feedback=feedback, cell_size=cell,
        seed=None if seed is None else int(seed),
    )
    return _result(processes.pitting(field, **options))


def strata(vol, bounds, resolution, thickness, normal, depth, wobble, seed, run=None):
    """Bedding: hard and soft layers weathering into ledges and overhangs.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`.
    thickness : float, optional
        Bed thickness, in mm. Defaults to 10.
    normal : :class:`compas.geometry.Vector`, optional
        Perpendicular to the beds. Tilt it from vertical to dip them. Defaults
        to slightly off vertical, which reads as rock rather than as a stack.
    depth : float, optional
        Millimetres removed from the softest beds. Defaults to 5.
    wobble : float, optional
        How far the beds wander, in mm. ``0`` keeps them flat. Defaults to 3.
    seed : int, optional
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    Raises
    ------
    ValueError
        For a normal that is horizontal or nearly so, which would make the
        beds vertical. The bedding is a height field, so it cannot express
        those; rotate the object instead.

    See Also
    --------
    :func:`compas_vol.processes.strata`

    Examples
    --------
    >>> from compas.geometry import Vector
    >>> layered, _ = strata(box(None, 20.0, None, None, 0), 14.0, 24, 5.0, Vector(0, 0, 1), 1.0, 0, 0)
    >>> layered.values.shape
    (24, 24, 24)
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    dip = None
    if normal is not None:
        nx, ny, nz = (float(v) for v in normal)
        if abs(nz) < 0.1 * max(abs(nx), abs(ny), 1e-12):
            raise ValueError("normal is too close to horizontal: beds steeper than about 84 degrees cannot be made.")
        dip = (nx / nz, ny / nz)
    options = _options(
        thickness=thickness, dip=dip, depth=depth, wobble=wobble, seed=None if seed is None else int(seed)
    )
    return _result(processes.strata(field, **options))


def runoff(vol, bounds, resolution, depth, decay, smooth, concentration, run=None):
    """Rain: water gathers downhill over the top of the model and cuts gullies.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`.
    depth : float, optional
        Millimetres cut where the flow is heaviest. Defaults to 6.
    decay : float, optional
        How far the cut reaches below the surface, in mm. Defaults to 10.
    smooth : float, optional
        Blur on the flow, in voxels. Higher gives fewer, broader channels.
        Defaults to 0.9.
    concentration : float, optional
        Lower spreads the cutting out, higher gathers it into a few deep
        gullies. Defaults to 0.4.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.runoff`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    options = _options(depth=depth, decay=decay, smooth=smooth, concentration=concentration)
    return _result(processes.runoff(field, **options))


def jointing(vol, bounds, resolution, count, opening, reach, seed, points, run=None):
    """Joints: the mass breaks into blocks, the seams opening from outside in.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`.
    count : int, optional
        Number of blocks, when ``points`` is not given. Defaults to 25.
    opening : float, optional
        Seam width at the surface, in mm. Defaults to 2.5.
    reach : float, optional
        How far in the seams stay open, in mm. Larger than the model cuts it
        into loose blocks. Defaults to 12.
    seed : int, optional
    points : list[:class:`compas.geometry.Point`], optional
        Block centres, to place the joints by hand. ``None`` entries are
        dropped; an empty list counts as unwired.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.jointing`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    points = [list(p) for p in (points or []) if p is not None] or None
    options = _options(
        count=None if count is None else int(count), opening=opening, reach=reach,
        seed=None if seed is None else int(seed), points=points,
    )
    return _result(processes.jointing(field, **options))


def fingering(vol, bounds, resolution, height, length, gain, wavelength, run=None):
    """Growth that folds into lobes and valleys: the brain-coral mechanism.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`, except that the surface grows: leave
        ``height`` of room around the model, or the folds are cut at the box.
    height : float, optional
        Millimetres the fastest part of the surface advances. Defaults to 30.
        The step count follows from it and from the resolution, so a finer
        grid takes longer and folds more finely, but grows as far.
    length : float, optional
        Length curvature is measured against, in mm. Defaults to 9.
    gain : float, optional
        Strength of the folding. ``0`` grows evenly; past about 1.5 lobes
        pinch off. Defaults to 1.4.
    wavelength : float, optional
        Roughly the width of a fold, in mm. Defaults to 4.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.fingering`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    options = _options(height=height, length=length, gain=gain, wavelength=wavelength)
    return _result(processes.fingering(field, **options))


def accretion(vol, bounds, resolution, height, reach, shelter, run=None):
    """Growth that fills hollows: deposition settling where it is sheltered.

    The opposite bias to :func:`pitting`, and a way to soften a model that
    weathering has left too jagged to build.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`fingering`.
    height : float, optional
        Millimetres deposited in the most sheltered places. Defaults to 4.
    reach : float, optional
        How far around each point shelter is measured, in mm. Defaults to 8.
    shelter : float, optional
        How strongly deposition prefers hollows. ``0`` coats everything
        evenly. Defaults to 1.6.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.accretion`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    return _result(processes.accretion(field, **_options(height=height, reach=reach, shelter=shelter)))


def branching(bounds, resolution, root, attractors, step, influence, thin, thick, seed, run=None):
    """A branching network grown by space colonization, drawn as a solid.

    Parameters
    ----------
    bounds : float | sequence
        The box to grow into. Required: there is no starting shape.
    resolution : int, optional
        Samples per axis. Defaults to 64.
    root : :class:`compas.geometry.Point`, optional
        Where growth starts. Defaults to the middle of the floor of the box.
    attractors : int, optional
        Points competing to be reached; more gives a denser network.
        Defaults to 800.
    step : float, optional
        Length of one growth step, in mm. Defaults to 3.5.
    influence : float, optional
        How far a tip can be pulled from, in mm. Defaults to 22.
    thin, thick : float, optional
        Radius of the finest twig and of the trunk, in mm. Default to 1.5
        and 5.
    seed : int, optional
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.branching`
    """
    if run is False:
        return None, None
    from compas_vol import processes
    from compas_vol.meshing import normalize_bounds

    if bounds is None:
        return None, None
    x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
    if root is None:
        root = ((x0 + x1) / 2, (y0 + y1) / 2, None)
    radius = (_float(thin, 1.5), _float(thick, 5.0))
    options = _options(
        attractors=None if attractors is None else int(attractors), step=step, influence=influence,
        seed=None if seed is None else int(seed),
    )
    return _result(
        processes.branching(bounds, int(resolution or 64), root=tuple(root), radius=radius, **options)
    )


def spinodal(bounds, resolution, feature, fraction, steps, seed, run=None):
    """A bicontinuous foam by phase separation: an aperiodic TPMS.

    Parameters
    ----------
    bounds : float | sequence
        The box to fill. Required. The result tiles across its faces.
    resolution : int, optional
        Samples per axis. Defaults to 64.
    feature : float, optional
        Wall and pore size, in mm. Defaults to 8.
    fraction : float, optional
        Solid fraction, in ``(0, 1)``, and exact. Below about 0.3 the solid
        breaks into islands. Defaults to 0.45.
    steps : int, optional
        Longer coarsens and smooths the structure. Defaults to 400.
    seed : int, optional
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.spinodal`

    Examples
    --------
    >>> foam, _ = spinodal(20.0, 24, 6.0, 0.4, 40, 0)
    >>> round(float((foam.values < 0).mean()), 1)
    0.4
    """
    if run is False:
        return None, None
    from compas_vol import processes

    if bounds is None:
        return None, None
    options = _options(
        feature=feature, fraction=fraction, steps=None if steps is None else int(steps),
        seed=None if seed is None else int(seed),
    )
    return _result(processes.spinodal(bounds, int(resolution or 64), **options))


def reactiondiffusion(bounds, resolution, feed, kill, steps, level, seed, run=None):
    """Gray-Scott reaction-diffusion, set solid: spots, worms and labyrinths.

    The least predictable of the processes. The pattern scales with the
    *grid*, not with the box, and neighbouring ``feed``/``kill`` values give
    patterns that look nothing alike -- or nothing at all, which raises.

    Parameters
    ----------
    bounds : float | sequence
        The box to fill. Required.
    resolution : int, optional
        Samples per axis. Defaults to 64.
    feed, kill : float, optional
        The reaction. Default to 0.037 and 0.06; for labyrinths, try feed in
        0.02 to 0.04 and kill in 0.05 to 0.065.
    steps : int, optional
        Defaults to 1500.
    level : float, optional
        Concentration taken as the surface. Defaults to 0.25.
    seed : int, optional
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    See Also
    --------
    :func:`compas_vol.processes.reaction_diffusion`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    if bounds is None:
        return None, None
    options = _options(
        feed=feed, kill=kill, steps=None if steps is None else int(steps), level=level,
        seed=None if seed is None else int(seed),
    )
    return _result(processes.reaction_diffusion(bounds, int(resolution or 64), **options))


def morphology(vol, bounds, resolution, operation, radius, run=None):
    """Enforce a minimum feature size: remove what is too thin, or fill what is too narrow.

    The clean-up after a process. Opening removes every wall, strut and
    fragment thinner than ``2 * radius``; closing fills every gap narrower
    than that and rejoins pieces that nearly touch. What is larger keeps its
    dimensions, to within about half a voxel.

    Parameters
    ----------
    vol, bounds, resolution
        As for :func:`abrasion`.
    operation : str, optional
        ``"open"`` or ``"close"``. Defaults to open.
    radius : float, optional
        Half the thinnest feature to keep, or the widest gap to fill, in mm.
        Defaults to 1.
    run : bool, optional
        ``False`` skips the work and returns ``(None, None)``. On the canvas the
        component holds its last result instead, so a slow process can be
        paused while things upstream change; unwired, it runs.

    Returns
    -------
    tuple[:class:`compas_vol.primitives.VolGrid`, str] | tuple[None, None]

    Raises
    ------
    ValueError
        For an operation that is neither, or one that leaves no surface.

    See Also
    --------
    :func:`compas_vol.processes.opened`, :func:`compas_vol.processes.closed`
    """
    if run is False:
        return None, None
    from compas_vol import processes

    name = (operation or "open").strip().lower()
    functions = {"open": processes.opened, "close": processes.closed}
    if name not in functions:
        raise ValueError('operation must be open or close; got "{}".'.format(operation))
    field = _field(vol, bounds, resolution)
    if field is None:
        return None, None
    return _result(functions[name](field, _float(radius, 1.0)))


# ==============================================================================
# meshing and fabrication
# ==============================================================================


def mesh(vol, bounds, resolution, level):
    """Sample a volumetric object over a box and extract its surface.

    Parameters
    ----------
    vol : :class:`compas_vol.base.VolObject`
        The object to mesh.
    bounds : float | sequence
        The domain, in any form :func:`compas_vol.meshing.normalize_bounds`
        accepts. Optional for a :class:`compas_vol.primitives.VolGrid`, such
        as a process result, which is then meshed over its own grid.
    resolution : int, optional
        Samples per axis. Defaults to 64, or to the grid's own.
    level : float, optional
        Iso-value. ``0`` is the surface; positive offsets outward.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`] | tuple[None, None]
        Vertices ``(n, 3)`` and triangle indices ``(m, 3)``. The component
        turns them into a Rhino mesh; a script hands them to
        :func:`compas_vol.meshing.write_stl`.
    """
    from compas_vol.meshing import generate_vertices_and_faces

    bounds, resolution = _grid_domain(vol, bounds, resolution)
    if vol is None or bounds is None:
        return None, None
    resolution = resolution if isinstance(resolution, tuple) else int(resolution or 64)
    return generate_vertices_and_faces(vol, bounds, resolution, level=_float(level, 0.0))


def inspect(vol, bounds, resolution, angle, min_wall):
    """Check a volumetric object for the things that stop a model printing.

    Parameters
    ----------
    vol : :class:`compas_vol.base.VolObject`
        The object to check.
    bounds : float | sequence
        The domain, as for :func:`mesh`, and like it optional for a grid.
    resolution : int, optional
        Samples per axis. Defaults to 96, or to the grid's own.
    angle : float, optional
        Overhang threshold from vertical, in degrees. Defaults to 45.
    min_wall : float, optional
        Thinnest printable wall, in model units. Defaults to 1.6.

    Returns
    -------
    tuple[str, bool, int] | tuple[None, None, None]
        The findings as text, whether the part is ready, and how many separate
        pieces it is. The full :class:`compas_vol.fabrication.Report` is what
        :func:`compas_vol.fabrication.inspect` returns, for a script that wants
        more than the component shows.

    Examples
    --------
    >>> text, ok, pieces = inspect(sphere(None, 8.0), 10.0, 32, None, None)
    >>> ok, pieces
    (True, 1)
    """
    from compas_vol import fabrication
    from compas_vol.meshing import sample

    bounds, resolution = _grid_domain(vol, bounds, resolution)
    if vol is None or bounds is None:
        return None, None, None
    resolution = resolution if isinstance(resolution, tuple) else int(resolution or 96)
    values, origin, spacing = sample(vol, bounds, resolution)
    report = fabrication.inspect(
        values,
        spacing=spacing,
        origin=origin,
        angle=float(angle) if angle else 45.0,
        min_wall=float(min_wall) if min_wall else 1.6,
    )
    return str(report), report.ok, report.pieces


# ==============================================================================
# utilities
# ==============================================================================


def info(refresh):
    """Report what compas_vol can do here, and what is missing.

    Parameters
    ----------
    refresh : bool
        Ignored. On the canvas, toggling it makes the component run again
        after something was installed.

    Returns
    -------
    tuple[str, str, bool]
        The report, the context (``"headless"``, ``"viewer"`` or ``"rhino"``)
        and whether meshing is available, which is the minimum for anything
        visible to come out of the components.

    Examples
    --------
    >>> text, where, ready = info(None)
    >>> where in ("headless", "viewer", "rhino")
    True
    """
    from compas_vol.runtime import capabilities
    from compas_vol.runtime import context
    from compas_vol.runtime import report

    return report(), context(), capabilities()["skimage"]
