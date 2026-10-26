"""
********************************************************************************
compas_vol.ghpython
********************************************************************************

.. currentmodule:: compas_vol.ghpython

Grasshopper integration.

Rhino 8 embeds CPython 3.9 and can import ordinary site packages, so the
Grasshopper components here are thin: each one converts its inputs with the
functions below, calls one function of :mod:`compas_vol.nodes` -- the same
component, without Grasshopper -- and converts the result back. Everything
worth testing therefore lives in the library rather than in the components,
because a ``code.py`` inside a ``.ghuser`` can only be run by Grasshopper.

The conversions read Rhino objects by their attributes rather than by type,
so they import nothing from Rhino until a Rhino object has to be *built*, and
are tested outside Rhino with stand-ins.

The components are in ``components/``, one folder each, holding the
``code.py``, ``metadata.json`` and 24x24 ``icon.png`` that ``ghuser-builder``
compiles into a ``.ghuser``. See ``docs/development.rst`` for how they are built
and installed.

.. autosummary::
    :toctree: generated/
    :nosignatures:

    point_to_compas
    vector_to_compas
    plane_to_frame
    box_to_bounds
    mesh_to_rhino
    to_rhino_mesh

"""

from compas_vol.runtime import require

__all__ = ["point_to_compas", "vector_to_compas", "plane_to_frame", "box_to_bounds", "mesh_to_rhino", "to_rhino_mesh"]


def point_to_compas(point):
    """Turn a Rhino point into a COMPAS one, passing ``None`` through.

    Parameters
    ----------
    point : :class:`Rhino.Geometry.Point3d` | None
        Anything with ``X``, ``Y`` and ``Z``.

    Returns
    -------
    :class:`compas.geometry.Point` | None
    """
    from compas.geometry import Point

    if point is None:
        return None
    return Point(point.X, point.Y, point.Z)


def vector_to_compas(vector):
    """Turn a Rhino vector into a COMPAS one, passing ``None`` through.

    Parameters
    ----------
    vector : :class:`Rhino.Geometry.Vector3d` | None
        Anything with ``X``, ``Y`` and ``Z``.

    Returns
    -------
    :class:`compas.geometry.Vector` | None
    """
    from compas.geometry import Vector

    if vector is None:
        return None
    return Vector(vector.X, vector.Y, vector.Z)


def plane_to_frame(plane):
    """Turn a Rhino plane into a COMPAS frame, passing ``None`` through.

    Parameters
    ----------
    plane : :class:`Rhino.Geometry.Plane` | None
        Anything with ``Origin``, ``XAxis`` and ``YAxis``.

    Returns
    -------
    :class:`compas.geometry.Frame` | None
        ``None`` lets the node fall back to world XY.
    """
    from compas.geometry import Frame

    if plane is None:
        return None
    o, x, y = plane.Origin, plane.XAxis, plane.YAxis
    return Frame([o.X, o.Y, o.Z], [x.X, x.Y, x.Z], [y.X, y.Y, y.Z])


def box_to_bounds(box):
    """Turn a Rhino box, or anything with a bounding box, into sampling bounds.

    Parameters
    ----------
    box : :class:`Rhino.Geometry.Box` | :class:`Rhino.Geometry.BoundingBox` | :class:`Rhino.Geometry.GeometryBase`
        The domain to sample over, or ``None``. Grasshopper hands boxes over as
        ``Rhino.Geometry.Box``; any geometry with ``GetBoundingBox`` works too,
        which lets a designer wire in a bounding Brep instead.

    Returns
    -------
    tuple[float, float, float, float, float, float] | None
        ``(xmin, ymin, zmin, xmax, ymax, zmax)``, the form
        :func:`compas_vol.meshing.normalize_bounds` already accepts. ``None``
        passes through.

    Notes
    -----
    Only the axis-aligned extent is used. A rotated Grasshopper box samples
    its bounding box, not its own frame -- rotate the volumetric object
    instead, with :class:`compas_vol.modifications.VolTransformation`.
    """
    if box is None:
        return None
    bbox = box
    if hasattr(box, "BoundingBox"):
        bbox = box.BoundingBox
    elif hasattr(box, "GetBoundingBox"):
        bbox = box.GetBoundingBox(True)
    lo, hi = bbox.Min, bbox.Max
    return (lo.X, lo.Y, lo.Z, hi.X, hi.Y, hi.Z)


def to_rhino_mesh(obj, bounds, resolution=64, level=0.0, workers=None):
    """Sample a volumetric object and hand Grasshopper a Rhino mesh.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        What to mesh.
    bounds : :class:`Rhino.Geometry.Box` | float | sequence
        The domain. A Rhino box is converted with :func:`box_to_bounds`;
        anything else goes to :func:`compas_vol.meshing.normalize_bounds`.
    resolution : int | tuple[int, int, int]
        Samples along each axis.
    level : float
        The iso-value to extract. ``0`` is the surface; a positive value
        offsets outward, a negative one inward, in model units for a metric
        field.
    workers : int, optional
        Sampling threads. See :func:`compas_vol.meshing.sample`.

    Returns
    -------
    :class:`Rhino.Geometry.Mesh`

    Raises
    ------
    ImportError
        Outside Rhino, where there is no ``Rhino.Geometry`` to build.

    Notes
    -----
    Building the Rhino mesh is a per-vertex and per-face loop through
    RhinoCommon, so it costs far more per triangle than the marching cubes
    that produced them. That is the reason this path is for design iteration:
    keep the resolution modest here, and export the final model headless with
    :func:`compas_vol.meshing.export_stl`, which writes the same geometry
    about 45x faster.
    """
    from compas_vol.meshing import generate_vertices_and_faces

    if not isinstance(bounds, (int, float, list, tuple)):
        bounds = box_to_bounds(bounds)
    vertices, faces = generate_vertices_and_faces(obj, bounds, resolution, level=level, workers=workers)
    return mesh_to_rhino(vertices, faces)


def mesh_to_rhino(vertices, faces):
    """Build a Rhino mesh from arrays of vertices and triangles.

    ``compas_rhino.conversions`` has an equivalent, but it takes COMPAS lists
    and would mean converting the arrays twice. This reads the arrays directly
    and computes the normals Grasshopper needs for shading.

    Parameters
    ----------
    vertices : array-like
        ``(n, 3)`` coordinates, as :func:`compas_vol.nodes.mesh` returns them.
    faces : array-like
        ``(m, 3)`` vertex indices.

    Returns
    -------
    :class:`Rhino.Geometry.Mesh` | None
        ``None`` when there is nothing to build.

    Raises
    ------
    ImportError
        Outside Rhino.
    """
    if vertices is None or faces is None:
        return None
    geometry = require("Rhino.Geometry")
    mesh = geometry.Mesh()
    add_vertex = mesh.Vertices.Add
    for x, y, z in vertices:
        add_vertex(float(x), float(y), float(z))
    add_face = mesh.Faces.AddFace
    for a, b, c in faces:
        add_face(int(a), int(b), int(c))
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh
