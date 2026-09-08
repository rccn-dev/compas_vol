"""Shared plumbing for the volumetric modelling examples.

Every example here is really about one thing: the CSG tree. The sampling,
meshing, viewing and slice inspection around it are identical, so they live
here instead of being copy-pasted into each script.

See ``template.py`` for the same pipeline written out step by step, without
this module, if you want to see what it is doing underneath.

Requires the ``examples`` extra::

    uv sync --extra examples
"""

import os

import numpy as np

from compas_vol.meshing import generate_mesh
from compas_vol.meshing import normalize_bounds
from compas_vol.meshing import sample

#: The default modelling domain used by the examples: a 40mm cube.
BOUNDS = (-20.0, -20.0, -20.0, 20.0, 20.0, 20.0)

#: The default sampling resolution. Drop this to ~80 for quick iteration.
RESOLUTION = 160

AXES = {"x": 0, "y": 1, "z": 2}


def export_stl(mesh, name, directory=None):
    """Write a mesh to an STL file next to the example scripts.

    Parameters
    ----------
    mesh : :class:`compas.datastructures.Mesh`
        The mesh to write.
    name : str
        The file stem; ``.stl`` is appended.
    directory : str, optional
        Where to write. Defaults to this file's directory.

    Returns
    -------
    str
        The path written to.
    """
    directory = directory or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(directory, "{}.stl".format(name))
    # COMPAS 2's Mesh.to_stl takes a path, not an open file object.
    mesh.to_stl(path, binary=True)
    return path


def show_mesh(mesh, **kwargs):
    """Open a mesh in the COMPAS viewer. Blocks until the window is closed."""
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(mesh)
    viewer.show()
    return viewer


def show_field(shape, bounds=BOUNDS, resolution=RESOLUTION, axis="z", title=None):
    """Open an interactive slice through the signed distance field.

    Drag the slider to move the cutting plane. Blue is inside the solid,
    red is outside, and the black contour is the surface itself -- the same
    zero level set that :func:`compas_vol.meshing.generate_mesh` triangulates.

    Parameters
    ----------
    shape : :class:`compas_vol.base.VolObject` | :class:`numpy.ndarray`
        The object to inspect, or an already-sampled distance matrix.
    bounds : sequence
        The sampling domain. See :func:`compas_vol.meshing.normalize_bounds`.
    resolution : int | tuple[int, int, int]
        The sampling resolution. Ignored if ``shape`` is already an array.
    axis : {'x', 'y', 'z'}
        The axis to slice along.
    title : str, optional
        A title for the figure.
    """
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider

    if isinstance(shape, np.ndarray):
        field = shape
    else:
        field, _, _ = sample(shape, bounds, resolution)

    x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
    index = AXES[axis]

    # The two in-plane axes, and their world extents.
    plane = [i for i in range(3) if i != index]
    labels = [("X", "Y", "Z")[i] for i in plane]
    lo = [(x0, y0, z0)[i] for i in plane]
    hi = [(x1, y1, z1)[i] for i in plane]
    depth_lo, depth_hi = (x0, y0, z0)[index], (x1, y1, z1)[index]
    n = field.shape[index]

    def slice_at(i):
        return np.take(field, i, axis=index).T

    initial = n // 2
    data = slice_at(initial)

    # Symmetric limits so that zero sits exactly at the centre of the diverging
    # colormap. The old scripts hard-coded +/-1, which clipped most fields to
    # solid red and blue.
    limit = float(np.nanmax(np.abs(field)))
    limit = limit if limit > 0 else 1.0

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.subplots_adjust(left=0.25, bottom=0.2)

    extent = (lo[0], hi[0], lo[1], hi[1])
    img = ax.imshow(
        data, cmap="RdBu", vmin=-limit, vmax=limit, origin="lower", extent=extent
    )
    ax.set_xlabel("{} axis".format(labels[0]))
    ax.set_ylabel("{} axis".format(labels[1]))
    ax.set_aspect("equal")
    fig.colorbar(img, ax=ax, label="signed distance")

    gx = np.linspace(lo[0], hi[0], data.shape[1])
    gy = np.linspace(lo[1], hi[1], data.shape[0])
    contour = ax.contour(gx, gy, data, levels=[0.0], colors="black", linewidths=1.0)

    def depth_of(i):
        return depth_lo + (depth_hi - depth_lo) * i / max(n - 1, 1)

    heading = title or "signed distance field"
    ax.set_title("{}\n{} = {:.2f}".format(heading, axis.upper(), depth_of(initial)))

    slider_ax = fig.add_axes([0.1, 0.2, 0.03, 0.65])
    slider = Slider(
        ax=slider_ax,
        label="{}\nslice".format(axis.upper()),
        valmin=0,
        valmax=n - 1,
        valstep=1,
        valinit=initial,
        orientation="vertical",
    )

    def update(value):
        nonlocal contour
        i = int(value)
        current = slice_at(i)
        img.set_data(current)
        # Contour sets cannot be updated in place, so replace them.
        contour.remove()
        contour = ax.contour(gx, gy, current, levels=[0.0], colors="black", linewidths=1.0)
        ax.set_title("{}\n{} = {:.2f}".format(heading, axis.upper(), depth_of(i)))
        fig.canvas.draw_idle()

    slider.on_changed(update)

    # Keep a reference on the figure so the widget is not garbage collected.
    fig._slider = slider
    plt.show()
    return fig


def demo(shape, name, bounds=BOUNDS, resolution=RESOLUTION, export=False, axis="z", recenter=False):
    """Mesh a volumetric object, view it, then inspect its field.

    The viewer blocks until you close it; the slice inspector opens after.

    Parameters
    ----------
    shape : :class:`compas_vol.base.VolObject`
        The object to show.
    name : str
        Used for the window title and the STL file stem.
    bounds : sequence
        The modelling domain.
    resolution : int | tuple[int, int, int]
        The sampling resolution.
    export : bool
        Write ``<name>.stl`` next to the scripts. Off by default so that
        running an example does not drop a large file in the repository.
    axis : {'x', 'y', 'z'}
        The axis for the slice inspector.
    recenter : bool
        Move the mesh so its centroid sits at the world origin.

    Returns
    -------
    :class:`compas.datastructures.Mesh`
    """
    from compas.geometry import Translation
    from compas.geometry import Vector

    print("meshing {} at resolution {} ...".format(name, resolution))
    mesh = generate_mesh(shape, bounds, resolution)
    print("  {} vertices, {} faces".format(mesh.number_of_vertices(), mesh.number_of_faces()))

    if recenter:
        mesh.transform(Translation.from_vector(-Vector(*mesh.centroid())))

    if export:
        print("  wrote {}".format(export_stl(mesh, name)))

    show_mesh(mesh)
    show_field(shape, bounds, resolution, axis=axis, title=name)
    return mesh
