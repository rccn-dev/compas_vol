"""A periodic strut lattice, trimmed to a box."""

from compas.geometry import Box
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.microstructures import Lattice
from compas_vol.primitives import VolBox

lat = Lattice(7, 5.0, 0.5, frame=Frame((1, 0, 0), (1, 0.2, 0.1), (-0.3, 1, 0.2)))
print(lat.typenames)
print(lat.lattice_type)

# Trim the infinite lattice to a finite block.
shape = Intersection(lat, VolBox(Box(24, 20, 16), 1.0))

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(shape, bounds=((-14, 14), (-12, 12), (-10, 10)), resolution=(112, 96, 80))
    viewer.show()
