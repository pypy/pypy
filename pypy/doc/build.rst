.. _building-from-source:

Building PyPy from Source
=========================

Building PyPy requires a Python2 interpreter since RPython is a Python2
dialect. For building PyPy, we recommend installing a pre-built PyPy2.7 first
(see :doc:`install`). It is possible to build PyPy with CPython2.7, but it will
take a lot longer to run -- depending on your architecture, between two and
three times as long.

Even when using PyPy2.7 to build PyPy, translation is time-consuming -- 20
minutes on a fast machine -- and RAM-hungry.  You will need **at least** 3 GB
of memory on a 32-bit machine and 6GB on a 64-bit machine.

Before you start
----------------

Our normal development workflow avoids a full translation by using test-driven
development. You can read more about how to develop PyPy here_, and latest
translated (hopefully functional) binary packages are available on our
buildbot's `nightly builds`_

.. _here: contributing.html
.. _`nightly builds`: https://buildbot.pypy.org/nightly

You will need the build dependencies below to run the tests.

Clone the repository
--------------------

If you prefer to compile your own PyPy, or if you want to modify it, you
will need to obtain a copy of the sources.  This can be done either by
`downloading them from the download page`_ or by checking them out from the
repository using git.  We suggest using git if you want to access
the current development.

.. _downloading them from the download page: https://www.pypy.org/download.html

You must issue the following command on your
command line, DOS box, or terminal::

    git clone https://github.com/pypy/pypy.git

This will clone the repository and place it into a directory
named ``pypy``, and will get you the PyPy source in ``pypy/pypy`` and
documentation files in ``pypy/pypy/doc``.
We try to ensure that the tip is always stable, but it might
occasionally be broken.  You may want to check out `our nightly tests`_:
find a revision hash, e.g. "963e808156b3", that passed at least the
``{linux64}`` tests (corresponding to a ``+`` sign on the
line ``success``) and then, in your cloned repository, switch to this revision
using::

    git checkout XXXXX

where XXXXX is the revision hash.

.. _our nightly tests: https://buildbot.pypy.org/summary?branch=main


Install build-time dependencies
-------------------------------
(**Note**: for some hints on how to translate the Python interpreter under
Windows, see the `windows document`_ . 

.. _`windows document`: windows.html
.. _`RPython documentation`: https://rpython.readthedocs.org

The host Python2 needs to have CFFI installed. If translating on PyPy, CFFI
is already installed. If translating on CPython, you need to install it, e.g.
using ``python2.7 -mpip install cffi``.

To build PyPy on Unix using the C translation backend, you need at least a C
compiler and ``make`` installed. Further, some optional modules have additional
dependencies:

cffi, ctypes
    libffi, pkg-config

zlib
    libz

bz2
    libbz2

pyexpat
    libexpat1

_vmprof
    libunwind (optional, loaded dynamically at runtime)

Make sure to have these libraries (with development headers) installed
before building PyPy, otherwise the resulting binary will not contain
these modules.  Furthermore, the following libraries should be present
after building PyPy, otherwise the corresponding CFFI modules are not
built (you can run or re-run `lib_pypy/pypy_tools/build_cffi_imports.py`_ to
build them; you don't need to re-translate the whole PyPy):

.. _`lib_pypy/pypy_tools/build_cffi_imports.py`: https://github.com/pypy/pypy/blob/main/lib_pypy/pypy_tools/build_cffi_imports.py

sqlite3
    libsqlite3

_ssl, _hashlib
    libssl

curses
    libncurses-dev   (for PyPy2)
    libncursesw-dev  (for PyPy3)

gdbm
    libgdbm-dev

tk
    tk-dev

lzma (PyPy3 only)
    liblzma or libxz, version 5 and up

To run untranslated tests, you need the Boehm garbage collector libgc, version
7.4 and up

On Debian and Ubuntu (16.04 onwards), this is the command to install
all build-time dependencies::

    apt-get install gcc make libffi-dev pkg-config zlib1g-dev libbz2-dev \
    libsqlite3-dev libncurses5-dev libexpat1-dev libssl-dev libgdbm-dev \
    tk-dev libgc-dev \
    liblzma-dev libncursesw5-dev     # these two only needed on PyPy3

On Fedora::

    dnf install gcc make libffi-devel pkgconfig zlib-devel bzip2-devel \
    sqlite-devel ncurses-devel expat-devel openssl-devel tk-devel \
    gdbm-devel gc-devel\
    xz-devel  # For lzma on PyPy3.

On SLES11::

    zypper install gcc make python-devel pkg-config \
    zlib-devel libopenssl-devel libbz2-devel sqlite3-devel \
    libexpat-devel libffi-devel \
    xz-devel # For lzma on PyPy3.
    (XXX plus the SLES11 version of libgdbm-dev and tk-dev)

On Mac OS X:

Currently PyPy supports both building on both Apple Silicon (M1, Arm64) and
X86_64. You must use an appropriate toolchain for building: either ``arm64``
or ``x86_64``. "Fat" universal2 builds are not supported.

Most of the build-time dependencies are installed alongside the Developer
Tools. ``libx11`` is needed for ``tkinter``.  ``openssl`` needs to be
installed for tests, and a brew-provided pypy will speed up translation. Note
that you must use the architecture-appropriate x86_64 or arm64 ``brew``
command:

.. code-block:: shell

    xcode-select --install
	brew install openssl pypy pkg-config libx11
    # expose openssl in the cffi _ssl_build script
    export CPPFLAGS=$(pkg-config openssl --cflags-only-I)
    export LDFLAGS=$(pkg-config openssl --libs-only-L)


Set environment variables that will affect translation
------------------------------------------------------

The following environment variables can be used to tweak the result:

+------------------------+-----------------------------------------------------------+
| value                  | result                                                    |
+------------------------+-----------------------------------------------------------+
| CC                     | compiler to use                                           |
+------------------------+-----------------------------------------------------------+
| PYPY_MULTIARCH         | pypy 3.7+: ends up in ``sys.platform._multiarch``         |
|                        | on posix, defaults to ``x86_64-linux-gnu``                |
+------------------------+-----------------------------------------------------------+
| PYPY_USESSION_DIR      | base directory for temporary files, usually ``$TMP``      |
+------------------------+-----------------------------------------------------------+
| PYPY_USESSION_BASENAME | each call to ``from rpython.tools import udir`` will get  |
|                        | a temporary directory                                     |
|                        | ``$PYPY_USESSION_DIR/usession-$PYPY_USESSION_BASENAME-N`` |
|                        | where ``N`` increments on each call                       |
+------------------------+-----------------------------------------------------------+
| PYPY_USESSION_KEEP     | how many old temporary directories to keep, any older     |
|                        | ones will be deleted. Defaults to 3                       |
+------------------------+-----------------------------------------------------------+

Run the translation
-------------------

Since the translating Python needs CFFI, it is best to create a virtualenv and
then ``pip install cffi`` there.

We usually translate in the ``pypy/goal`` directory, so all the following
commands assume your ``$pwd`` is there.

Translate with JIT::

    pypy2.7 ../../rpython/bin/rpython --opt=jit

Translate without JIT::

    pypy2.7 ../../rpython/bin/rpython --opt=2

Note this translates pypy via the ``targetpypystandalone.py`` file, so these
are shorthand for::

    pypy2.7 ../../rpython/bin/rpython <rpython options> targetpypystandalone.py <pypy options>

More help is available via ``--help`` at either option position, and more info
can be found in the :doc:`config/index` section.

(You can use ``python2`` instead of ``pypy2.7`` here, which will take longer
but works too.)

If everything works correctly this will:

1. Run the rpython `translation chain`_, producing a database of the
   entire pypy interpreter. This step is currently single threaded, and RAM
   hungry. As part of this step,  the chain creates a large number of C code
   files and a Makefile to compile them in a
   directory controlled by the ``PYPY_USESSION_DIR`` environment variable.
2. Create an executable ``pypy-c`` or ``pypy3.XX-c`` by running the Makefile.
   This step can utilize all possible cores on the machine.
3. Copy the needed binaries to the current directory.
4. Generate c-extension modules for any cffi-based stdlib modules.


The resulting executable behaves mostly like a normal Python
interpreter (see :doc:`cpython_differences`), and is ready for testing, for
use as a base interpreter for a new virtualenv, or for packaging into a binary
suitable for installation on another machine running the same OS as the build
machine.

Note that step 4 is merely done as a convenience, any of the steps may be rerun
without rerunning the previous steps.

.. _`translation chain`: https://rpython.readthedocs.io/en/latest/translation.html


Making a debug build of PyPy
----------------------------

Rerun the ``Makefile`` with the ``make lldebug`` or ``make lldebug0`` target,
which will build in a way that running under a debugger makes sense.
Appropriate compilation flags are added to add debug info, and for ``lldebug0``
compiler optimizations are fully disabled. If you stop in a debugger, you will
see the very wordy machine-generated C code from the rpython translation step,
which takes a little bit of reading to relate back to the rpython code.

Build cffi import libraries for the stdlib
------------------------------------------

Various stdlib modules require a separate build step to create the cffi
import libraries in the :ref:`out-of-line API mode <performance>`. This is done by the following
command::

   cd pypy/goal
   PYTHONPATH=../.. ./pypy-c ../../lib_pypy/pypy_tools/build_cffi_imports.py


Packaging (preparing for installation)
--------------------------------------

Packaging is required if you want to install PyPy system-wide, even to
install on the same machine.  The reason is that doing so prepares a
number of extra features that cannot be done lazily on a root-installed
PyPy, because the normal users don't have write access.  This concerns
mostly libraries that would normally be compiled if and when they are
imported the first time.

::

    python pypy/tool/release/package.py --archive-name=pypy-VER-PLATFORM

This creates a clean and prepared hierarchy, as well as a ``.tar.bz2``
with the same content; the directory to find these will be printed out.  You
can then either move the file hierarchy or unpack the ``.tar.bz2`` at the
correct place.

It is recommended to use package.py because custom scripts will
invariably become out-of-date.  If you want to write custom scripts
anyway, note an easy-to-miss point: some modules are written with CFFI,
and require some compilation.  If you install PyPy as root without
pre-compiling them, normal users will get errors.

Installation
------------

PyPy dynamically finds the location of its libraries depending on the location
of the executable. The directory hierarchy of a typical PyPy2 installation
looks like this::

    ./bin/pypy
    ./include/
    ./lib_pypy/
    ./lib-python/2.7
    ./site-packages/

A PyPy3.8+ installation will match the CPython layout::

    ./bin/
    ./include/pypy3.8/include
    ./lib/pypy3.8

The hierarchy shown above is relative to a PREFIX directory. PREFIX is
computed by starting from the directory where the executable resides, and
"walking up" the filesystem until we find a directory containing ``lib_pypy``
and ``lib-python/2.7`` (on pypy2).

To install PyPy system wide on unix-like systems, it is recommended to put the
whole hierarchy alone (e.g. in ``/opt/pypy``) and put a symlink to the
``pypy`` executable into ``/usr/bin`` or ``/usr/local/bin``.

If the executable fails to find suitable libraries, it will report ``debug:
WARNING: library path not found, using compiled-in sys.path`` and then attempt
to continue normally. If the default path is usable, most code will be fine.
However, the ``sys.prefix`` will be unset and some existing libraries assume
that this is never the case.
