class Blur(object):
    """Gaussian blur of a sampled distance matrix.

    Unlike the other modifications this operates on an already-sampled grid
    rather than on a volumetric object, so it does not implement the
    ``get_distance`` interface and cannot be composed into a tree.

    Requires the ``meshing`` extra (``pip install compas-vol[meshing]``) for SciPy.

    Parameters
    ----------
    distance_matrix : :class:`numpy.ndarray`
        The original distance matrix, of shape ``(nx, ny, nz)``.
    radius : float
        The standard deviation of the Gaussian kernel.

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.modifications import Blur
    >>> dm = np.random.default_rng(0).random((8, 8, 8))
    >>> Blur(dm, 1.0).get_blurred().shape
    (8, 8, 8)
    """

    def __init__(self, distance_matrix, radius=3.0):
        self.distance_matrix = distance_matrix
        self.radius = radius

    def __repr__(self):
        return "Blur(<array>, {})".format(self.radius)

    def get_blurred(self):
        """Return a blurred copy of the distance matrix.

        Returns
        -------
        :class:`numpy.ndarray`
            The blurred matrix, same shape as the input.
        """
        # ``scipy.ndimage.filters`` was a deprecated shim removed in SciPy 1.15.
        from scipy.ndimage import gaussian_filter

        return gaussian_filter(self.distance_matrix, sigma=self.radius)
