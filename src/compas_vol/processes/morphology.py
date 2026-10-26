"""Minimum feature size, enforced rather than hoped for."""

import numpy as np

__all__ = ["opened", "closed"]


def opened(field, radius):
    """Remove everything thinner than ``2 * radius``, keeping the rest as it was.

    Morphological opening: erode the solid by a ball, then dilate it back.
    What survives is exactly the part of the model that a ball of that radius
    can roll through, so every wall, strut and spike thinner than twice the
    radius is gone -- along with any loose fragment too small to contain the
    ball. Everything thicker keeps its dimensions.

    This is the honest way to hold a minimum feature size. Tuning parameters
    until nothing looks too thin leaves the guarantee resting on the render;
    opening makes it a property of the geometry, and one that can be checked.

    Both steps redistance, because a constant offset of a field is only a
    distance field again away from the features it just removed. Each pass
    carries a sub-voxel error, so what survives comes back within roughly half
    a voxel of where it was, not exactly.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    radius : float
        Half the thinnest feature to keep, in mm. For printing, a sensible
        value is half the minimum wall the process can hold -- three nozzle
        widths, say.

    Returns
    -------
    :class:`compas_vol.processes.Field`

    Raises
    ------
    ValueError
        If nothing in the model is thicker than ``2 * radius``, so opening
        leaves nothing at all.

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.processes import Field, opened
    >>> x, y, z = np.ogrid[-10:10:41j, -10:10:41j, -10:10:41j]
    >>> ball = Field(np.sqrt(x**2 + y**2 + z**2) - 6.0, (-10, -10, -10), (0.5, 0.5, 0.5))
    >>> bool(abs(opened(ball, 2.0).values.min() + 6.0) < 0.5)   # the 6 mm ball survives
    True
    """
    try:
        eroded = field.copy(field.values + radius).redistanced()
        grown = eroded.copy(eroded.values - radius)
        # Opening only ever removes. Without this, a field with a `keep`
        # constraint would come back larger: the kept part survives the
        # erosion untouched and is then grown by the dilation.
        grown = grown.copy(np.maximum(grown.values, field.values)).redistanced()
    except ValueError:
        raise ValueError(
            "Opening by {} mm left nothing: no part of the model is thicker than {} mm.".format(radius, 2 * radius)
        )
    return grown.record("opened", radius=radius)


def closed(field, radius):
    """Fill every gap narrower than ``2 * radius``, keeping the rest as it was.

    The complement of :func:`opened`: dilate the solid by a ball, then erode
    it back. Gaps, slots and cracks too narrow for the ball are filled, and
    pieces that came within that distance of each other are joined -- useful
    for pulling a model that has broken into fragments back into one part,
    and for closing the hairline seams a process can leave behind.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    radius : float
        Half the widest gap to fill, in mm.

    Returns
    -------
    :class:`compas_vol.processes.Field`

    Raises
    ------
    ValueError
        If closing fills the whole domain, leaving no surface.
    """
    try:
        grown = field.copy(field.values - radius).redistanced()
        shrunk = grown.copy(grown.values + radius)
        # Closing only ever adds -- the mirror of `opened`, for a field
        # confined `within` an envelope.
        shrunk = shrunk.copy(np.minimum(shrunk.values, field.values)).redistanced()
    except ValueError:
        raise ValueError(
            "Closing by {} mm filled the whole domain: every gap is narrower than {} mm.".format(radius, 2 * radius)
        )
    return shrunk.record("closed", radius=radius)
