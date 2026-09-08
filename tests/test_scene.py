"""Scene object registration, the COMPAS 2 way of drawing volumetric objects."""

import importlib.util

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

import compas_vol
from compas_vol.base import VolObject
from compas_vol.combinations import Subtraction
from compas_vol.microstructures import TPMS
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

viewer_available = importlib.util.find_spec("compas_viewer") is not None
requires_viewer = pytest.mark.skipif(not viewer_available, reason="needs the viewer extra")


@pytest.fixture
def shape():
    return Subtraction(
        VolBox(Box(20, 15, 10), 2.5), VolSphere(Sphere(9, point=Point(5, 6, 0)))
    )


@pytest.fixture
def viewer():
    from compas_viewer import Viewer

    # Viewer is a singleton, so tests share one instance and one scene.
    return Viewer()


class TestPluginDeclaration:
    """These hold without compas_viewer installed."""

    def test_package_declares_its_plugin_module(self):
        assert compas_vol.__all_plugins__ == ["compas_vol.scene"]

    def test_plugin_module_imports_without_a_viewer(self):
        """compas_vol.scene must not hard-require compas_viewer at import time."""
        import compas_vol.scene as scene

        assert hasattr(scene, "register_scene_objects")

    def test_package_name_is_discoverable_by_compas(self):
        """COMPAS only scans top-level packages whose name starts with 'compas'."""
        import pkgutil

        names = [m for _i, m, is_pkg in pkgutil.iter_modules() if is_pkg and m.startswith("compas")]
        assert "compas_vol" in names


@requires_viewer
class TestSceneObject:
    def test_volobject_resolves_to_the_registered_scene_object(self, viewer, shape):
        from compas_vol.scene import VolObjectSceneObject

        obj = viewer.scene.add(shape, bounds=20.0, resolution=32)
        assert isinstance(obj, VolObjectSceneObject)

    def test_registration_resolves_through_the_mro(self, viewer):
        """Registering the VolObject base must cover every subclass."""
        from compas_vol.scene import VolObjectSceneObject

        for item in [
            VolBox(Box(10, 10, 10)),
            TPMS("Gyroid", 5.0),
            Subtraction(VolBox(Box(10, 10, 10)), VolSphere(Sphere(3))),
        ]:
            assert isinstance(item, VolObject)
            obj = viewer.scene.add(item, bounds=10.0, resolution=16)
            assert isinstance(obj, VolObjectSceneObject)

    def test_item_stays_the_volumetric_object(self, viewer, shape):
        """The scene object must not quietly swap the item for its mesh."""
        obj = viewer.scene.add(shape, bounds=20.0, resolution=32)
        assert obj.item is shape
        assert obj.volobject is shape

    def test_mesh_is_generated_from_the_field(self, viewer, shape):
        obj = viewer.scene.add(shape, bounds=20.0, resolution=32)
        assert isinstance(obj.mesh, Mesh)
        assert obj.mesh.number_of_faces() > 0

    def test_mesh_is_cached(self, viewer, shape):
        obj = viewer.scene.add(shape, bounds=20.0, resolution=32)
        assert obj.mesh is obj.mesh

    def test_resolution_is_honoured(self, viewer, shape):
        coarse = viewer.scene.add(shape, bounds=20.0, resolution=24)
        fine = viewer.scene.add(shape, bounds=20.0, resolution=64)
        assert fine.mesh.number_of_faces() > coarse.mesh.number_of_faces()

    def test_regenerate_resamples(self, viewer, shape):
        obj = viewer.scene.add(shape, bounds=20.0, resolution=24)
        before = obj.mesh.number_of_faces()
        after = obj.regenerate(resolution=64).number_of_faces()
        assert after > before

    def test_bounds_are_required_with_a_useful_message(self, viewer, shape):
        """Unlike a Shape's u/v, there is no sensible default sampling domain."""
        with pytest.raises(ValueError, match="bounds"):
            viewer.scene.add(shape)

    def test_level_offsets_the_surface(self, viewer):
        import numpy as np

        vs = VolSphere(Sphere(5, point=Point(0, 0, 0)))
        obj = viewer.scene.add(vs, bounds=10.0, resolution=48, level=2.0)
        pts = np.array([obj.mesh.vertex_coordinates(v) for v in obj.mesh.vertices()])
        np.testing.assert_allclose(np.linalg.norm(pts, axis=1), 7.0, atol=0.1)


@requires_viewer
class TestNoViewerWrapper:
    """Drawing goes through scene.add; there is no second way to do it."""

    def test_utilities_exposes_no_viewer_module(self):
        import importlib

        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("compas_vol.utilities.viewer")

    def test_scene_add_is_the_whole_api(self, viewer, shape):
        obj = viewer.scene.add(shape, bounds=20.0, resolution=24)
        assert obj.mesh.number_of_faces() > 0
