Building PyPy from Source
=========================

For building PyPy, it is recommended to install a pre-build PyPy first (see
:doc:`install`). It is possible to build PyPy with CPython, but it will take a
lot longer to run -- depending on your architecture, between two and three
times as long.

Even when using PyPy to build PyPy, translation is time-consuming -- 30
minutes on a fast machine -- and RAM-hungry.  You will need **at least** 2 GB
of memory on a 32-bit machine and 4GB on a 64-bit machine.


Install build-time dependencies
-------------------------------

To build PyPy on Unix using the C translation backend, you need at least a C
compiler and ``make`` installed. Further, some optional modules have additional
dependencies:

cffi, ctypes
    libffi, pkg-config

zlib
    libz

bz2
    libbz2

sqlite3
    libsqlite3

curses
    libncurses + cffi dependencies from above

pyexpat
    libexpat1

_ssl
    libssl

Make sure to have these libraries (with development headers) installed before
building PyPy, otherwise the resulting binary will not contain these modules.

On Debian, this is the command to install all build-time dependencies::

    apt-get install gcc make libffi-dev pkg-config libz-dev libbz2-dev \
    libsqlite3-dev libncurses-dev libexpat1-dev libssl-dev

On Fedora::

    yum install gcc make libffi-devel pkgconfig zlib-devel bzip2-devel \
    lib-sqlite3-devel ncurses-devel expat-devel openssl-devel


Run the translation
-------------------

Translate with JIT::

    pypy rpython/bin/rpython --opt=jit pypy/goal/targetpypystandalone.py

Translate without JIT::

    pypy rpython/bin/rpython --opt=2 pypy/goal/targetpypystandalone.py

If everything works correctly this will create an executable ``pypy-c`` in the
current directory. The executable behaves mostly like a normal Python
interpreter (see :doc:`cpython differences`).


Installation
------------

PyPy dynamically finds the location of its libraries depending on the location
of the executable. The directory hierarchy of a typical PyPy installation
looks like this::

    ./bin/pypy
    ./include/
    ./lib_pypy/
    ./lib-python/2.7
    ./site-packages/

The hierarchy shown above is relative to a PREFIX directory. PREFIX is
computed by starting from the directory where the executable resides, and
"walking up" the filesystem until we find a directory containing ``lib_pypy``
and ``lib-python/2.7``.

To install PyPy system wide on unix-like systems, it is recommended to put the
whole hierarchy alone (e.g. in ``/opt/pypy``) and put a symlink to the
``pypy`` executable into ``/usr/bin`` or ``/usr/local/bin``.

If the executable fails to find suitable libraries, it will report ``debug:
WARNING: library path not found, using compiled-in sys.path`` and then attempt
to continue normally. If the default path is usable, most code will be fine.
However, the ``sys.prefix`` will be unset and some existing libraries assume
that this is never the case.


.. TODO windows
