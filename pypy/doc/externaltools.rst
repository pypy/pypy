.. include:: throwaway.rst

External tools&programs needed by PyPy
======================================

Tools needed for testing
------------------------

These tools are used in various ways by PyPy tests; if they are not found,
some tests might be skipped, so they need to be installed on every buildbot
slave to be sure we actually run all tests:

  - Mono (versions 1.2.1.1 and 1.9.1 known to work)

  - Java/JVM (preferably sun-jdk; version 1.6.0 known to work)

  - Jasmin >= 2.2 (copy it from wyvern, /usr/local/bin/jasmin and /usr/local/share/jasmin.jar)

  - gcc

  - make

  - Some libraries (these are Debian package names, adapt as needed):

    * ``python-dev``
    * ``python-ctypes``
    * ``libffi-dev``
    * ``libz-dev`` (for the optional ``zlib`` module)
    * ``libbz2-dev`` (for the optional ``bz2`` module)
    * ``libncurses-dev`` (for the optional ``_minimal_curses`` module)
    * ``libgc-dev`` (only when translating with `--opt=0, 1` or `size`)
