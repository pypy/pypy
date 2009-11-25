If turned on, PyPy accepts to import a module ``x`` if it finds a
file ``x.pyc`` even if there is no file ``x.py``.

This is the way that CPython behaves, but it is disabled by
default for PyPy because it is a common cause of issues: most
typically, the ``x.py`` file is removed (manually or by a
version control system) but the ``x`` module remains
accidentally importable because the ``x.pyc`` file stays
around.

The usual reason for wanting this feature is to distribute
non-open-source Python programs by distributing ``pyc`` files
only, but this use case is not practical for PyPy at the
moment because multiple versions of PyPy compiled with various
optimizations might be unable to load each other's ``pyc``
files.
