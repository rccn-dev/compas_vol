import math

import numpy as np
import pytest
from compas.geometry import Box
from compas.geometry import Cone
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere
from compas.geometry import Torus

from compas_vol.analysis import Curvature
from compas_vol.analysis import Gradient
from compas_vol.combinations import LINEAR
from compas_vol.combinations import QUADRATIC
from compas_vol.combinations import Addition
from compas_vol.combinations import Blend
from compas_vol.combinations import Division
from compas_vol.combinations import Intersection
from compas_vol.combinations import Morph
from compas_vol.combinations import Multiplication
from compas_vol.combinations import SmoothIntersection
from compas_vol.combinations import SmoothSubtraction
from compas_vol.combinations import SmoothUnion
from compas_vol.combinations import SmoothUnionList
from compas_vol.combinations import Subtraction
from compas_vol.combinations import Union
from compas_vol.microstructures import TPMS
from compas_vol.microstructures import Lattice
from compas_vol.microstructures import LatticePolar
from compas_vol.microstructures import TPMSAttractor
from compas_vol.microstructures import TPMSPolar
from compas_vol.microstructures import TPMSSolid
from compas_vol.microstructures import Voronoi
from compas_vol.modifications import Factor
from compas_vol.modifications import MultiShell
from compas_vol.modifications import Overlay
from compas_vol.modifications import Offset
from compas_vol.modifications import Remap
from compas_vol.modifications import Shell
from compas_vol.modifications import Sine
from compas_vol.modifications import Conform
from compas_vol.modifications import Twist
from compas_vol.modifications import VolTransformation
from compas_vol.primitives import GDF
from compas_vol.primitives import Heart
from compas_vol.primitives import PlatonicSolid
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolCapsule
from compas_vol.primitives import VolCone
from compas_vol.primitives import VolCylinder
from compas_vol.primitives import VolEgg
from compas_vol.primitives import VolEllipsoid
from compas_vol.primitives import VolExtrusion
from compas_vol.primitives import VolGrid
from compas_vol.primitives import VolPlane
from compas_vol.primitives import VolPolyhedron
from compas_vol.primitives import VolSphere
from compas_vol.primitives import VolTorus

#: A frame that is neither axis-aligned nor origin-centred, so that any
#: mismatch between the single-point and vectorized transforms shows up.
SKEW_FRAME = Frame((1, 2, 3), (1, 0.3, 0.1), (-0.4, 1, 0.3))

_SQUARE = [(-5, -5, 0), (5, -5, 0), (5, 5, 0), (-5, 5, 0), (-5, -5, 0)]


def _heptagon_planes():
    planes = []
    for i in range(7):
        a = math.pi * 2 * i / 7
        x, y = math.cos(a), math.sin(a)
        planes.append(VolPlane(Plane((9 * x, 9 * y, 0), (x, y, 0))))
    planes.append(VolPlane(Plane((0, 0, 4), (0, 0, 1))))
    planes.append(VolPlane(Plane((0, 0, -4), (0, 0, -1))))
    return planes


def build_objects():
    """One instance of every volumetric class, keyed by a readable id."""
    vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    vb = VolBox(Box(20, 15, 10, frame=SKEW_FRAME), 2.5)
    vp = VolPlane(Plane((0, 0, 0), (0.2, 0.3, 1)))
    spheres = [VolSphere(Sphere(4, point=Point(i * 5, 0, 0))) for i in range(3)]

    return {
        # primitives
        "VolBox": vb,
        "VolBox-sharp": VolBox(Box(20, 15, 10), 0.0),
        "VolSphere": vs,
        "VolCylinder": VolCylinder(Cylinder(5, 7, frame=SKEW_FRAME)),
        "VolCone": VolCone(Cone(5, 7, frame=SKEW_FRAME)),
        "VolTorus": VolTorus(Torus(7.0, 4.0, frame=SKEW_FRAME)),
        "VolEllipsoid": VolEllipsoid(14, 10, 6, frame=SKEW_FRAME),
        "VolEgg": VolEgg(3, 4, 0.1, frame=SKEW_FRAME),
        "VolCapsule": VolCapsule(((-9, -6, 0), (6, 9, 0)), 5.0),
        "VolPlane": vp,
        "VolPolyhedron": VolPolyhedron(_heptagon_planes()),
        "VolExtrusion": VolExtrusion(_SQUARE, 10.0, frame=SKEW_FRAME),
        "Heart": Heart(30, frame=SKEW_FRAME),
        "PlatonicSolid-tetra": PlatonicSolid(10.0, 0, frame=SKEW_FRAME),
        "PlatonicSolid-octa": PlatonicSolid(10.0, 1, frame=SKEW_FRAME),
        "PlatonicSolid-dodeca": PlatonicSolid(10.0, 2, frame=SKEW_FRAME),
        "PlatonicSolid-icosa": PlatonicSolid(10.0, 3, frame=SKEW_FRAME),
        "GDF": GDF(10.0, "icosahedron", frame=SKEW_FRAME),
        "GDF-blended": GDF(10.0, "octahedron", exponent=4.0),
        # A sampled field, so the shared checks cover the bridge that every
        # process result comes back through.
        "VolGrid": VolGrid(
            np.sqrt(
                (np.linspace(-20, 20, 24)[:, None, None]) ** 2
                + (np.linspace(-20, 20, 24)[None, :, None]) ** 2
                + (np.linspace(-20, 20, 24)[None, None, :]) ** 2
            )
            - 9.0,
            (-20, -20, -20),
            (40 / 23, 40 / 23, 40 / 23),
        ),
        # combinations
        "Union": Union(vs, vb),
        "Union-list": Union([vs, vb, vp]),
        "Intersection": Intersection(vs, vb),
        "Subtraction": Subtraction(vb, vs),
        "SmoothUnion": SmoothUnion(vs, vb, 1.5),
        "SmoothIntersection": SmoothIntersection(vs, vb, 1.5),
        "SmoothSubtraction": SmoothSubtraction(vb, vs, 1.5),
        "SmoothUnionList": SmoothUnionList(spheres, 1.0),
        "Morph": Morph(vs, vb, 0.5),
        "Blend-linear": Blend(vs, vb, vp, 5.0, LINEAR),
        "Blend-quadratic": Blend(vs, vb, vp, 5.0, QUADRATIC),
        "Addition": Addition(vs, vb),
        "Multiplication": Multiplication(vs, vb),
        "Division": Division(vs, vb),
        # modifications
        "Shell": Shell(Union(vs, vb), 2.5, 0.5),
        "MultiShell": MultiShell(vb, 1.0, 2.5),
        "Overlay": Overlay(vs, vb, 0.2),
        "Factor": Factor(vb, 2.0),
        "Sine": Sine(vb, 0.5),
        "Twist": Twist(vb, Frame((0, 0, 0), (1, 0, 0), (0, 0, 1)), 0.05),
        "Conform": Conform(TPMSSolid("Gyroid", 6.0, 1.2), vs, axis=2, scale=1.5, offset=0.4),
        "VolTransformation": VolTransformation(vb, SKEW_FRAME),
        "Offset": Offset(vb, 1.5),
        "Offset-driven": Offset(vs, Remap(vp, (-10.0, 10.0), (-1.0, 2.0))),
        "Remap-linear": Remap(vs, (-5.0, 20.0), (2.0, 0.5)),
        "Remap-smooth": Remap(vp, (-10.0, 10.0), (0.0, 1.0), "smooth"),
        # microstructures
        "Lattice": Lattice(5, 5.0, 0.3, frame=SKEW_FRAME),
        "LatticePolar": LatticePolar(5, 5.0, 0.3, 6, frame=SKEW_FRAME),
        "TPMS-gyroid": TPMS("Gyroid", 5.0),
        "TPMS-schwarzp": TPMS("SchwarzP", 5.0),
        "TPMS-diamond": TPMS("Diamond", 5.0),
        "TPMS-neovius": TPMS("Neovius", 5.0),
        "TPMS-lidinoid": TPMS("Lidinoid", 5.0),
        "TPMS-fischerkoch": TPMS("FischerKoch", 5.0),
        "TPMS-iwp": TPMS("IWP", 5.0),
        "TPMSSolid-sheet": TPMSSolid("Gyroid", 8.0, 1.2),
        "TPMSSolid-network": TPMSSolid("SchwarzP", 8.0, mode="network", offset=0.5, frame=SKEW_FRAME),
        "TPMSSolid-network-inverted": TPMSSolid("IWP", 8.0, mode="network", invert=True),
        "TPMSSolid-graded": TPMSSolid(
            "Diamond", 8.0, Remap(vs, (0.0, 20.0), (2.0, 0.6)), offset=Remap(vp, (-9, 9), (-0.5, 0.5))
        ),
        "TPMSPolar": TPMSPolar("Gyroid", 5.0, 0.1, 6),
        "TPMSAttractor": TPMSAttractor(vs, "Gyroid", (2.0, 8.0), (0.0, 20.0)),
        "Voronoi": Voronoi(
            [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10), (-8, 3, 4), (6, -7, 2)], 1.0
        ),
        "Voronoi-cells": Voronoi([(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)], 1.0, walls=False),
    }


ALL_OBJECTS = build_objects()


def pytest_generate_tests(metafunc):
    """Parametrize any test asking for ``volobject`` over every class."""
    if "volobject" in metafunc.fixturenames:
        metafunc.parametrize(
            "volobject",
            list(ALL_OBJECTS.values()),
            ids=list(ALL_OBJECTS.keys()),
        )


@pytest.fixture
def sphere():
    return VolSphere(Sphere(5, point=Point(0, 0, 0)))


@pytest.fixture
def gradient(sphere):
    return Gradient(sphere, 0.01)


@pytest.fixture
def curvature(sphere):
    return Curvature(sphere, 0.1)
