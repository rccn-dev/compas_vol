"""Every volumetric object must survive a COMPAS JSON round trip."""

import pytest
from compas.data import json_dumps
from compas.data import json_loads

from compas_vol.base import VolObject


def test_is_a_compas_data_object(volobject):
    assert isinstance(volobject, VolObject)


def test_json_roundtrip_preserves_type(volobject):
    restored = json_loads(json_dumps(volobject))
    assert type(restored) is type(volobject)


def test_json_roundtrip_preserves_field(volobject):
    """The restored object must evaluate identically, children included."""
    restored = json_loads(json_dumps(volobject))

    for point in [(0, 0, 0), (3, 4, 5), (-7, 2, -1), (12, -8, 6)]:
        assert restored.get_distance(point) == pytest.approx(
            volobject.get_distance(point), rel=1e-12, abs=1e-12
        )


def test_copy_is_independent(volobject):
    """copy() comes from compas.data.Data and must produce a working object."""
    duplicate = volobject.copy()
    assert type(duplicate) is type(volobject)
    assert duplicate.get_distance((3, 4, 5)) == pytest.approx(volobject.get_distance((3, 4, 5)))
