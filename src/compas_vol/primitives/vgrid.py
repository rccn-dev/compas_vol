import numpy as np

from compas_vol.base import VolObject
from compas_vol.runtime import require

__all__ = ["VolGrid"]

#: Points interpolated per pass. Big enough that the call overhead is
#: irrelevant, small enough that ten threads doing it at once stay in memory.
_CHUNK = 1 << 20


class VolGrid(VolObject):
    """A sampled distance field, interpolated between its samples.

    The bridge from the grid world back to the modelling world. A process --
    erosion, growth, phase separation -- produces values on a grid and nothing
    else; wrapping them here lets the result be shelled, cut, filled with a
    lattice and exported like any analytic object.

    Between samples the field is interpolated trilinearly. Outside the grid it
    keeps growing: the value at the edge plus the distance travelled from it,
    which is an upper bound on the true distance and keeps booleans sensible
    rather than undefined.

    Two things to know when modelling with one. Features smaller than about
    two voxels of the source grid are not in the data, so no amount of
    resolution downstream will bring them back. And the interpolated field is
    only as metric as the grid it came from, which is why processes redistance
    before handing it over.

    Parameters
    ----------
    values : array-like
        Signed distances, shape ``(nx, ny, nz)``, negative inside.
    origin : sequence[float]
        World coordinates of ``values[0, 0, 0]``.
    spacing : sequence[float]
        Voxel size along each axis.

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.primitives import VolGrid
    >>> x, y, z = np.ogrid[-10:10:41j, -10:10:41j, -10:10:41j]
    >>> ball = VolGrid(np.sqrt(x**2 + y**2 + z**2) - 5.0, (-10, -10, -10), (0.5, 0.5, 0.5))
    >>> round(ball.get_distance([0, 0, 0]), 6)
    -5.0
    >>> round(ball.get_distance([5, 0, 0]), 6)
    0.0
    """

    def __init__(self, values, origin=(0, 0, 0), spacing=(1, 1, 1), name=None):
        super().__init__(name=name)
        self._values = None
        self.values = values
        self.origin = tuple(float(v) for v in origin)
        self.spacing = tuple(float(v) for v in spacing)
        self.history = []

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        # Full precision, so a round trip is exact like every other object
        # here. That makes a VolGrid the bulkiest thing in the package by far
        # -- a 160^3 grid is over 100 MB of JSON -- so prefer storing the
        # recipe (the source object and the process parameters, which a
        # process result carries in `history`) and baking again.
        return {
            "values": self.values.tolist(),
            "origin": list(self.origin),
            "spacing": list(self.spacing),
            "history": self.history,
        }

    @classmethod
    def __from_data__(cls, data):
        grid = cls(data["values"], data["origin"], data["spacing"])
        grid.history = data.get("history", [])
        return grid

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def values(self):
        """:class:`numpy.ndarray`: The sampled distances."""
        return self._values

    @values.setter
    def values(self, values):
        values = np.asarray(values, dtype=float)
        if values.ndim != 3:
            raise ValueError("A VolGrid holds a 3D grid; got an array of shape {}.".format(values.shape))
        if min(values.shape) < 2:
            raise ValueError("A VolGrid needs at least two samples along each axis; got {}.".format(values.shape))
        self._values = values

    @property
    def bounds(self):
        """tuple: ``(xmin, ymin, zmin, xmax, ymax, zmax)`` covered by the grid."""
        return self.origin + tuple(o + (n - 1) * s for o, n, s in zip(self.origin, self.values.shape, self.spacing))

    def __repr__(self):
        return "VolGrid({}x{}x{} @ {:.3f})".format(*self.values.shape, min(self.spacing))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        return float(self.get_distance_numpy(np.array(p.x), np.array(p.y), np.array(p.z)))

    def get_distance_numpy(self, x, y, z):
        map_coordinates = require("scipy.ndimage").map_coordinates

        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
        count = int(np.prod(shape))
        broadcast = [np.broadcast_to(c, shape).ravel() for c in (x, y, z)]
        result = np.empty(count)

        # Interpolating a few million points at once costs several hundred
        # megabytes of index arrays, and `sample` evaluates the tree in ten
        # threads at once, so a grid-backed field can multiply that into
        # gigabytes and send the machine to swap. Chunking keeps the peak flat
        # at a cost that does not show up in the timings.
        for start in range(0, count, _CHUNK):
            stop = min(start + _CHUNK, count)
            indices = np.stack(
                [(c[start:stop] - o) / s for c, o, s in zip(broadcast, self.origin, self.spacing)]
            )
            inside = map_coordinates(self.values, indices, order=1, mode="nearest")

            # Outside the grid, map_coordinates clamps to the edge. Add the
            # distance back to the box, so the field keeps rising instead of
            # flattening into a plateau that booleans would read as solid.
            outside = np.zeros(stop - start)
            for axis, (n, step) in enumerate(zip(self.values.shape, self.spacing)):
                over = np.clip(indices[axis] - (n - 1), 0, None) + np.clip(-indices[axis], 0, None)
                outside += (over * step) ** 2
            result[start:stop] = inside + np.sqrt(outside)

        return result.reshape(shape)

    def gradient_magnitude(self):
        """:class:`numpy.ndarray`: ``|grad values|``, which is 1 for a true distance field."""
        gradients = np.gradient(self.values, *self.spacing)
        return np.sqrt(sum(g * g for g in gradients))

    def to_field(self):
        """:class:`compas_vol.processes.Field`: The grid back as a process field."""
        from compas_vol.processes import Field

        return Field(self.values, self.origin, self.spacing, self.history)

    @classmethod
    def from_object(cls, obj, bounds, resolution=128, workers=None, name=None):
        """Bake any volumetric object onto a grid.

        Useful on its own: an expensive tree (a Voronoi foam, a deep boolean
        stack) sampled once and reused is far cheaper to model with, at the
        cost of the resolution it was baked at.
        """
        from compas_vol.meshing import sample

        values, origin, spacing = sample(obj, bounds, resolution, workers=workers)
        return cls(values, origin, spacing, name=name or getattr(obj, "name", None))

    @classmethod
    def from_mesh(cls, mesh, resolution=96, padding=None, name=None):
        """Bake a closed mesh into a distance field.

        The way arbitrary geometry enters the field world. Until a mesh is a
        field it cannot be shelled, filled with a lattice, eroded or blended;
        once it is, it composes like a sphere. :class:`VolPolyhedron` only
        covers convex solids, so this is the general route -- a survey, a
        tessellated NURBS skin, or a relaxed shell from ``compas_tess``.

        Parameters
        ----------
        mesh : :class:`compas.datastructures.Mesh`
            A **closed** surface. An open one still returns a field, but its
            sign is meaningless, because there is no inside to be on.
        resolution : int | tuple[int, int, int]
            Samples along the longest axis, or along each axis. This is the
            finest feature the result can carry: the mesh is not consulted
            again afterwards.
        padding : float, optional
            Space left around the mesh, in model units. Defaults to a tenth
            of the longest side. The field keeps growing outside the grid, so
            the padding only has to cover the offsets and blends you intend.
        name : str, optional

        Returns
        -------
        :class:`VolGrid`

        Notes
        -----
        Two approximations, both bounded and both stated so they can be
        checked. The magnitude is the distance to a dense sampling of the
        surface rather than to the triangles themselves, with the samples
        placed closer together than half a voxel -- so the error is below the
        resolution of the grid it is written into. The sign is exact: it comes
        from counting triangle crossings, which needs no tolerance.

        What is *not* an approximation of this function is the mesh. A
        faceted sphere is genuinely smaller than the sphere it approximates,
        and this reports the mesh it was given.

        Examples
        --------
        >>> from compas.datastructures import Mesh
        >>> from compas.geometry import Box
        >>> from compas_vol.primitives import VolGrid
        >>> grid = VolGrid.from_mesh(Mesh.from_shape(Box(20.0)), resolution=64)
        >>> abs(grid.get_distance([0, 0, 0]) - -10.0) < 0.5   # the cube's half-width
        True
        >>> abs(grid.get_distance([20, 0, 0]) - 10.0) < 0.5   # 10 mm clear of its face
        True

        The half-millimetre tolerance is not slack in the method: it is the
        voxel. A baked field knows what it was sampled at and no more, which
        is why the resolution is an argument rather than a default worth
        forgetting.
        """
        from ._mesh_field import signed_distance_to_mesh

        points = np.asarray([mesh.vertex_coordinates(k) for k in mesh.vertices()], dtype=float)
        low, high = points.min(axis=0), points.max(axis=0)
        if padding is None:
            padding = 0.1 * float((high - low).max())
        low, high = low - padding, high + padding

        counts = (resolution,) * 3 if isinstance(resolution, (int, float)) else tuple(resolution)
        if isinstance(resolution, (int, float)):
            # One sample size in every direction, so cells stay cubic and a
            # wall measures the same thickness whichever way it faces.
            step = float((high - low).max()) / (int(resolution) - 1)
            counts = tuple(max(2, int(np.ceil(extent / step)) + 1) for extent in (high - low))
            spacing = (step,) * 3
        else:
            counts = tuple(int(v) for v in counts)
            spacing = tuple((high[i] - low[i]) / (counts[i] - 1) for i in range(3))

        values = signed_distance_to_mesh(mesh, tuple(low), spacing, counts)
        return cls(values, tuple(low), spacing, name=name or getattr(mesh, "name", None))
