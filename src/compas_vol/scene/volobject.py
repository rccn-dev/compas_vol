from compas_viewer.scene import MeshObject

from compas_vol.meshing import generate_mesh


class VolObjectSceneObject(MeshObject):
    """Scene object for displaying a volumetric object in the COMPAS viewer.

    A volumetric object is an implicit function, so it has to be sampled and
    iso-surfaced before it can be drawn. That is the same situation a
    :class:`compas.geometry.Shape` is in -- a sphere has to be tessellated
    before it has any vertices -- and it is handled the same way: the sampling
    parameters ride along on the ``scene.add`` call, exactly as ``u`` and ``v``
    do for :class:`compas_viewer.scene.ShapeObject`.

    Unlike ``u``/``v`` there is no sensible default for ``bounds``. A
    :class:`compas_vol.microstructures.TPMS` or
    :class:`compas_vol.microstructures.Lattice` is infinite, and a
    :class:`compas_vol.combinations.Intersection` cannot report an extent
    either, so the caller has to say where to look.

    Parameters
    ----------
    bounds : :class:`compas.geometry.Box` | float | sequence
        The sampling domain. See :func:`compas_vol.meshing.normalize_bounds`.
        Required.
    resolution : int | tuple[int, int, int], optional
        The number of samples along each axis. Default is ``64``.
    level : float, optional
        The iso-value to extract. Default is ``0.0``, the object's surface.
    **kwargs
        Passed on to :class:`compas_viewer.scene.MeshObject`.

    Attributes
    ----------
    item : :class:`compas_vol.base.VolObject`
        The volumetric object being displayed.
    mesh : :class:`compas.datastructures.Mesh`
        The iso-surface of :attr:`item`, generated on first access.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere  # doctest: +SKIP
    >>> from compas_vol.primitives import VolBox, VolSphere  # doctest: +SKIP
    >>> from compas_vol.combinations import Subtraction  # doctest: +SKIP
    >>> from compas_viewer import Viewer  # doctest: +SKIP
    >>> shape = Subtraction(VolBox(Box(20, 15, 10), 2.5), VolSphere(Sphere(9)))  # doctest: +SKIP
    >>> viewer = Viewer()  # doctest: +SKIP
    >>> viewer.scene.add(shape, bounds=20.0, resolution=100)  # doctest: +SKIP
    >>> viewer.show()  # doctest: +SKIP
    """

    def __init__(self, bounds=None, resolution=64, level=0.0, **kwargs):
        if bounds is None:
            raise ValueError(
                "A volumetric object has no inherent extent, so it cannot be drawn without "
                "a sampling domain. Pass bounds to scene.add(), e.g. "
                "scene.add(obj, bounds=20.0, resolution=100)."
            )

        self._mesh = None
        self.bounds = bounds
        self.resolution = resolution
        self.level = level

        # An iso-surface is a dense triangle soup; its vertices and edges are
        # sampling artefacts rather than features worth drawing.
        kwargs.setdefault("show_points", False)
        kwargs.setdefault("show_lines", False)

        super().__init__(**kwargs)

    @property
    def volobject(self):
        """:class:`compas_vol.base.VolObject`: The volumetric object being displayed."""
        return self.item

    @property
    def mesh(self):
        # Overrides MeshObject.mesh, which returns self.item directly. Here the
        # item is the implicit object and the mesh is derived from it, so that
        # `.item` keeps pointing at what the caller actually added.
        if self._mesh is None:
            self._mesh = generate_mesh(self.item, self.bounds, self.resolution, self.level)
        return self._mesh

    @mesh.setter
    def mesh(self, mesh):
        self._mesh = mesh

    def regenerate(self, bounds=None, resolution=None, level=None):
        """Re-sample the object, optionally with new parameters.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The newly generated iso-surface.
        """
        if bounds is not None:
            self.bounds = bounds
        if resolution is not None:
            self.resolution = resolution
        if level is not None:
            self.level = level
        self._mesh = None
        return self.mesh
