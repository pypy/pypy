__all__ = ["__version__"]

import os as _os, sys as _sys
_v = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'vendored_packages')
if _os.path.isdir(_v) and _v not in _sys.path:
    _sys.path.insert(0, _v)
del _os, _sys, _v

try:
    from ._version import version as __version__
except ImportError:
    # broken installation, we don't even try
    # unknown only works because we do poor mans version compare
    __version__ = "unknown"
