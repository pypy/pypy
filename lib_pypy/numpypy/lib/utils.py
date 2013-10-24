import os

__all__ = ['get_include']

def get_include():
    """
    Return the directory that contains the NumPy \\*.h header files.

    Extension modules that need to compile against NumPy should use this
    function to locate the appropriate include directory.

    Notes
    -----
    When using ``distutils``, for example in ``setup.py``.
    ::

        import numpy as np
        ...
        Extension('extension_name', ...
                include_dirs=[np.get_include()])
        ...

    """
    return os.path.join(os.path.dirname(__file__), '../../../include')
