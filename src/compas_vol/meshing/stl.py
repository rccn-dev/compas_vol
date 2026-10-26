"""Writing STL files straight from arrays."""

import struct

__all__ = ["write_stl", "export_stl"]

# One binary STL record: a facet normal, three vertices, and the unused
# attribute count. Little-endian float32, as the format requires.
_FACET = [("normal", "<3f4"), ("vertices", "<3,3f4"), ("attributes", "<u2")]


def write_stl(filepath, vertices, faces, name="compas_vol"):
    """Write a triangle mesh to a binary STL file.

    Goes straight from arrays to bytes, which is what makes it fast: building
    a :class:`compas.datastructures.Mesh` and calling its ``to_stl`` costs
    about 45 times more for a mesh of a few million triangles, because both
    steps run in Python.

    Facet normals are computed from the winding of each triangle, so the
    output of :func:`generate_vertices_and_faces` comes out with its normals
    pointing out of the solid, as slicers expect.

    Parameters
    ----------
    filepath : str
        Where to write.
    vertices : array-like
        Vertex coordinates, shape ``(n, 3)``.
    faces : array-like
        Triangles, shape ``(m, 3)``, as indices into ``vertices``.
    name : str
        Written into the 80-byte header.

    Returns
    -------
    str
        The path written to.

    Raises
    ------
    ValueError
        If the faces are not triangles. STL has no other kind of facet;
        triangulate first, or use :meth:`compas.datastructures.Mesh.to_stl`.

    Examples
    --------
    >>> import os
    >>> import tempfile
    >>> from compas_vol.meshing import write_stl
    >>> vertices = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
    >>> faces = [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]
    >>> path = write_stl(os.path.join(tempfile.mkdtemp(), "tetra.stl"), vertices, faces)
    >>> os.path.getsize(path) == 84 + 4 * 50
    True
    """
    import numpy as np

    vertices = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces, dtype=np.intp)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("A binary STL holds triangles only; got faces of shape {}.".format(faces.shape))

    corners = vertices[faces]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    # A degenerate triangle has no normal. Zero is what most writers emit, and
    # slicers recompute it from the winding anyway.
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)

    facets = np.zeros(len(faces), dtype=np.dtype(_FACET))
    facets["normal"] = normals
    facets["vertices"] = corners

    # The header must not begin with "solid", or readers take the file for ASCII.
    header = "compas_vol {}".format(name).encode("ascii", "replace")[:80]
    with open(filepath, "wb") as f:
        f.write(header.ljust(80, b" "))
        f.write(struct.pack("<I", len(faces)))
        f.write(facets.tobytes())
    return filepath


def export_stl(obj, filepath, bounds, resolution=64, level=0.0, workers=None, name=None):
    """Sample, iso-surface and write a volumetric object as a binary STL.

    The print-ready path: field to file without building a COMPAS mesh on the
    way. Use :func:`generate_mesh` when you want the mesh itself, for a scene
    or for further modelling.

    Requires the ``meshing`` extra (``pip install compas-vol[meshing]``).

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to export.
    filepath : str
        Where to write.
    bounds : :class:`compas.geometry.Box` | float | sequence
        The sampling domain. See :func:`normalize_bounds`. It has to contain
        the solid with room to spare: anything reaching the edge of the domain
        is cut there and leaves the surface open.
    resolution : int | tuple[int, int, int]
        The number of samples along each axis.
    level : float
        The iso-value to extract.
    workers : int, optional
        Threads used for sampling. See :func:`sample`.
    name : str, optional
        Written into the STL header. Defaults to the object's name.

    Returns
    -------
    str
        The path written to.

    Examples
    --------
    >>> import os
    >>> import tempfile
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.meshing import export_stl
    >>> path = os.path.join(tempfile.mkdtemp(), "ball.stl")
    >>> export_stl(VolSphere(Sphere(5, point=Point(0, 0, 0))), path, 8.0, 32) == path
    True
    """
    from .marching import generate_vertices_and_faces

    vertices, faces = generate_vertices_and_faces(obj, bounds, resolution, level, workers=workers)
    return write_stl(filepath, vertices, faces, name=name or type(obj).__name__)
