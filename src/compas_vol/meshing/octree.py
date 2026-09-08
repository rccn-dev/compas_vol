from math import sqrt

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point

SQRT3 = sqrt(3.0)

__all__ = ["OctNode", "Octree"]


class OctNode(object):
    """A single cell of an :class:`Octree`.

    Parameters
    ----------
    x, y, z : float
        The centre of the cell.
    edgelength : float
        The edge length of the cell.
    level : int
        The subdivision depth of the cell. The root is level ``0``.
    """

    def __init__(self, x, y, z, edgelength, level):
        self.point = Point(x, y, z)
        self.edgelength = edgelength
        self._level = level
        self.branches = None

    def __repr__(self):
        return "OctNode({0}, {1}, {2}, {3}, {4})".format(
            self.point.x, self.point.y, self.point.z, self.edgelength, self.level
        )

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        # The COMPAS 1 setter coerced the level to float, which then broke the
        # integer depth comparison it was used in.
        self._level = int(level)

    @property
    def is_leaf(self):
        return self.branches is None

    @property
    def box(self):
        """:class:`compas.geometry.Box`: The cell as a COMPAS box."""
        return Box(
            self.edgelength,
            self.edgelength,
            self.edgelength,
            frame=Frame(self.point, (1, 0, 0), (0, 1, 0)),
        )

    def divide_node(self):
        """Split this cell into eight children."""
        self.branches = []
        qs = self.edgelength / 4.0
        nl = self.level + 1
        for dz in (-qs, qs):
            for dy in (-qs, qs):
                for dx in (-qs, qs):
                    self.branches.append(
                        OctNode(
                            self.point.x + dx,
                            self.point.y + dy,
                            self.point.z + dz,
                            qs * 2,
                            nl,
                        )
                    )


class Octree(object):
    """An adaptive octree that refines only where a distance field crosses zero.

    Subdividing only the cells the surface passes through gives a sparse
    description of the boundary, which is useful for adaptive meshing or for
    visualising where detail is concentrated.

    The COMPAS 1 version could not run: it never stored the object to sample,
    called ``get_distance`` with three separate coordinates instead of a point,
    and read a ``node.pos`` attribute that :class:`OctNode` never defined.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object whose surface to track.
    world_size : float
        The edge length of the root cell.
    max_level : int
        The maximum subdivision depth.
    center : point, optional
        The centre of the root cell. Defaults to the origin.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.meshing import Octree
    >>> tree = Octree(VolSphere(Sphere(30, point=Point(0, 0, 0))), 100.0, 3)
    >>> tree.build()
    >>> len(tree.leaves()) > 8
    True
    """

    def __init__(self, obj=None, world_size=100.0, max_level=4, center=None):
        self.obj = obj
        self.world_size = world_size
        self.max_level = max_level
        self.center = Point(*center) if center else Point(0, 0, 0)
        self.root = OctNode(self.center.x, self.center.y, self.center.z, world_size, 0)

    def __repr__(self):
        return "Octree({0!r}, {1}, {2})".format(self.obj, self.world_size, self.max_level)

    def build(self):
        """Subdivide the tree from the root down to :attr:`max_level`."""
        self.root = OctNode(self.center.x, self.center.y, self.center.z, self.world_size, 0)
        self.divide(self.root)

    def divide(self, node):
        """Recursively subdivide a node if the surface passes through it."""
        if node.level >= self.max_level:
            return
        d = self.obj.get_distance(node.point)
        # A cell can only contain the surface if the distance from its centre
        # is less than the distance to its own furthest corner.
        if abs(d) < SQRT3 * node.edgelength / 2.0:
            node.divide_node()
            for branch in node.branches:
                self.divide(branch)

    def leaves(self, node=None):
        """All leaf nodes of the tree.

        Returns
        -------
        list[:class:`OctNode`]
        """
        node = node or self.root
        if node.is_leaf:
            return [node]
        found = []
        for branch in node.branches:
            found.extend(self.leaves(branch))
        return found

    def surface_leaves(self, node=None):
        """The leaf nodes at :attr:`max_level` that the surface passes through.

        Returns
        -------
        list[:class:`OctNode`]
        """
        return [
            leaf
            for leaf in self.leaves(node)
            if abs(self.obj.get_distance(leaf.point)) < SQRT3 * leaf.edgelength / 2.0
        ]

    def to_boxes(self, surface_only=True):
        """The leaf cells as COMPAS boxes, for visualisation.

        Returns
        -------
        list[:class:`compas.geometry.Box`]
        """
        leaves = self.surface_leaves() if surface_only else self.leaves()
        return [leaf.box for leaf in leaves]
