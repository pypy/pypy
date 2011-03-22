"""
unit and functional testing with Python.
(pypy version of startup script)
see http://pytest.org for details.
"""
__all__ = ['main']

from _pytest.core import main, UsageError, _preloadplugins
from _pytest import core as cmdline
from _pytest import __version__

# This pytest.py script is located in the pypy source tree
# which has a copy of pytest and py within its source tree.
# If the environment also has an installed version of pytest/py
# we are bound to get warnings so we disable them.
# XXX eventually pytest and py should not be inlined shipped
# with the pypy source code but become a requirement for installation.

import warnings
warnings.filterwarnings("ignore",
    "Module py was already imported", category=UserWarning)
warnings.filterwarnings("ignore",
    "Module _pytest was already imported",
    category=UserWarning)
warnings.filterwarnings("ignore",
    "Module pytest was already imported",
    category=UserWarning)

if __name__ == '__main__': # if run as a script or by 'python -m pytest'
    raise SystemExit(main())
else:
    _preloadplugins() # to populate pytest.* namespace so help(pytest) works
