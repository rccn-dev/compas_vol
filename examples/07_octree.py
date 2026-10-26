"""Adaptive octree refinement around the surface of a field.

The volumetric object and the octree's boxes go into one viewer scene with
``scene.add``.
"""

from compas.colors import Color
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Subtraction
from compas_vol.meshing import Octree
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

vs = VolSphere(Sphere(9, point=Point(3, 3, 0)))
vb = VolBox(Box(20, 15, 10), 2.5)
shape = Subtraction(vb, vs)

tree = Octree(shape, world_size=40.0, max_level=4)
tree.build()

if __name__ == "__main__":
    from compas_viewer import Viewer

    boxes = tree.to_boxes(surface_only=True)
    print("{} leaves, {} on the surface".format(len(tree.leaves()), len(boxes)))

    viewer = Viewer()

    # The volumetric object goes straight into the scene; bounds and resolution
    # ride along the way u and v do for a compas Shape.
    viewer.scene.add(shape, bounds=20.0, resolution=100, opacity=0.5)

    for box in boxes:
        viewer.scene.add(box, show_faces=False, linecolor=Color(0.2, 0.5, 0.9))

    viewer.show()
