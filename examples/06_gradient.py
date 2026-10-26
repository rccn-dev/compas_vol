"""The gradient of a field, shown as colour on its surface.
"""

from compas.colors import Color
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.analysis import Gradient
from compas_vol.combinations import Union
from compas_vol.meshing import generate_mesh
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
vb = VolBox(Box(20, 15, 10), 2.5)
u = Union(vs, vb)

grad = Gradient(u, 0.01)

if __name__ == "__main__":
    from compas_viewer import Viewer

    mesh = generate_mesh(u, bounds=20.0, resolution=100)

    # Map the unit gradient at each vertex to an RGB colour.
    vertexcolor = {}
    for vertex in mesh.vertices():
        v = grad.get_gradient(Point(*mesh.vertex_coordinates(vertex)))
        vertexcolor[vertex] = Color(*[(c + 1) / 2 for c in (v.x, v.y, v.z)])

    viewer = Viewer()
    viewer.scene.add(
        mesh,
        show_points=False,
        show_lines=False,
        vertexcolor=vertexcolor,
        use_vertexcolors=True,
    )
    viewer.show()
