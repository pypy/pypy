Building PyPy from Source
=========================

For building PyPy, we recommend installing a pre-built PyPy first (see
:doc:`install`). It is possible to build PyPy with CPython, but it will take a
lot longer to run -- depending on your architecture, between two and three
times as long.

Even when using PyPy to build PyPy, translation is time-consuming -- 30
minutes on a fast machine -- and RAM-hungry.  You will need **at least** 2 GB
of memory on a 32-bit machine and 4GB on a 64-bit machine.

Before you start
----------------

Our normal development workflow avoids a full translation by using test-driven
development. You can read more about how to develop PyPy here_, and latest
translated (hopefully functional) binary packages are available on our
buildbot's `nightly builds`_

.. _here: getting-started-dev.html
.. _`nightly builds`: http://buildbot.pypy.org/nightly

You will need the build dependencies below to run the tests.

Clone the repository
--------------------

If you prefer to compile your own PyPy, or if you want to modify it, you
will need to obtain a copy of the sources.  This can be done either by
`downloading them from the download page`_ or by checking them out from the
repository using mercurial.  We suggest using mercurial if you want to access
the current development.

.. _downloading them from the download page: http://pypy.org/download.html

You must issue the following command on your
command line, DOS box, or terminal::

    hg clone http://bitbucket.org/pypy/pypy pypy

This will clone the repository and place it into a directory
named ``pypy``, and will get you the PyPy source in ``pypy/pypy`` and
documentation files in ``pypy/pypy/doc``.
We try to ensure that the tip is always stable, but it might
occasionally be broken.  You may want to check out `our nightly tests`_:
find a revision (12-chars alphanumeric string, e.g. "963e808156b3")
that passed at least the
``{linux32}`` tests (corresponding to a ``+`` sign on the
line ``success``) and then, in your cloned repository, switch to this revision
using::

    hg up -r XXXXX

where XXXXX is the revision id.

.. _our nightly tests: http://buildbot.pypy.org/summary?branch=<trunk>


Install build-time dependencies
-------------------------------
(**Note**: for some hints on how to translate the Python interpreter under
Windows, see the `windows document`_ . For hints on how to cross-compile in
a chroot using scratchbox2, see the `arm document`_ in the
`RPython documentation`_)

.. _`windows document`: windows.html
.. _`arm document`: http://rpython.readthedocs.org/en/latest/arm.html
.. _`RPython documentation`: http://rpython.readthedocs.org

The host Python needs to have CFFI installed. If translating on PyPy, CFFI is
already installed. If translating on CPython, you need to install it, e.g.
using ``pip install cffi``.

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

_ssl
    libssl

_vmprof
    libunwind (optional, loaded dynamically at runtime)

Make sure to have these libraries (with development headers) installed
before building PyPy, otherwise the resulting binary will not contain
these modules.  Furthermore, the following libraries should be present
after building PyPy, otherwise the corresponding CFFI modules are not
built (you can run or re-run `pypy/tool/release/package.py` to retry
to build them; you don't need to re-translate the whole PyPy):

sqlite3
    libsqlite3

curses
    libncurses-dev   (for PyPy2)
    libncursesw-dev  (for PyPy3)

gdbm
    libgdbm-dev

tk
    tk-dev

lzma (PyPy3 only)
    liblzma

To run untranslated tests, you need the Boehm garbage collector libgc.

On recent Debian and Ubuntu (like 17.04), this is the command to install
all build-time dependencies::

    apt-get install gcc make libffi-dev pkg-config zlib1g-dev libbz2-dev \
    libsqlite3-dev libncurses5-dev libexpat1-dev libssl-dev libgdbm-dev \
    tk-dev libgc-dev python-cffi \
    liblzma-dev libncursesw5-dev     # these two only needed on PyPy3

On older Debian and Ubuntu (12.04 to 16.04)::

    apt-get install gcc make libffi-dev pkg-config libz-dev libbz2-dev \
    libsqlite3-dev libncurses-dev libexpat1-dev libssl-dev libgdbm-dev \
    tk-dev libgc-dev python-cffi \
    liblzma-dev libncursesw-dev      # these two only needed on PyPy3

On Fedora::

    dnf install gcc make libffi-devel pkgconfig zlib-devel bzip2-devel \
    sqlite-devel ncurses-devel expat-devel openssl-devel tk-devel \
    gdbm-devel python-cffi\
    xz-devel  # For lzma on PyPy3.

On SLES11::

    zypper install gcc make python-devel pkg-config \
    zlib-devel libopenssl-devel libbz2-devel sqlite3-devel \
    libexpat-devel libffi-devel python-curses python-cffi \
    xz-devel # For lzma on PyPy3.
    (XXX plus the SLES11 version of libgdbm-dev and tk-dev)

On Mac OS X, most of these build-time dependencies are installed alongside
the Developer Tools. However, note that in order for the installation to
find them you may need to run::

    xcode-select --install


Run the translation
-------------------

We usually translate in the ``pypy/goal`` directory, so all the following
commands assume your ``$pwd`` is there.

Translate with JIT::

    pypy ../../rpython/bin/rpython --opt=jit

Translate without JIT::

    pypy ../../rpython/bin/rpython --opt=2

Note this translates pypy via the ``targetpypystandalone.py`` file, so these
are shorthand for::

    pypy ../../rpython/bin/rpython <rpython options> targetpypystandalone.py <pypy options>

More help is availabe via ``--help`` at either option position, and more info
can be found in the :doc:`config/index` section.

(You can use ``python`` instead of ``pypy`` here, which will take longer
but works too.)

If everything works correctly this will:

1. Run the rpython `translation chain`_, producing a database of the
   entire pypy interpreter. This step is currently singe threaded, and RAM
   hungry. As part of this step,  the chain creates a large number of C code
   files and a Makefile to compile them in a
   directory controlled by the ``PYPY_USESSION_DIR`` environment variable.  
2. Create an executable ``pypy-c`` by running the Makefile. This step can
   utilize all possible cores on the machine.  
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

If the Makefile is rerun with the lldebug or lldebug0 target, appropriate
compilation flags are added to add debug info and reduce compiler optimizations
to ``-O0`` respectively. If you stop in a debugger, you will see the
very wordy machine-generated C code from the rpython translation step, which
takes a little bit of reading to relate back to the rpython code.

Build cffi import libraries for the stdlib
------------------------------------------

Various stdlib modules require a separate build step to create the cffi
import libraries in the `out-of-line API mode`_. This is done by the following
command::

   cd pypy/goal
   PYTHONPATH=../.. ./pypy-c ../tool/build_cffi_imports.py

.. _`out-of-line API mode`: http://cffi.readthedocs.org/en/latest/overview.html#real-example-api-level-out-of-line

Packaging (preparing for installation)
--------------------------------------

Packaging is required if you want to install PyPy system-wide, even to
install on the same machine.  The reason is that doing so prepares a
number of extra features that cannot be done lazily on a root-installed
PyPy, because the normal users don't have write access.  This concerns
mostly libraries that would normally be compiled if and when they are
imported the first time.

::

    cd pypy/tool/release
    ./package.py --archive-name=pypy-VER-PLATFORM

This creates a clean and prepared hierarchy, as well as a ``.tar.bz2``
with the same content; both are found by default in
``/tmp/usession-YOURNAME/build/``.  You can then either move the file
hierarchy or unpack the ``.tar.bz2`` at the correct place.

It is recommended to use package.py because custom scripts will
invariably become out-of-date.  If you want to write custom scripts
anyway, note an easy-to-miss point: some modules are written with CFFI,
and require some compilation.  If you install PyPy as root without
pre-compiling them, normal users will get errors:

* PyPy 2.5.1 or earlier: normal users would see permission errors.
  Installers need to run ``pypy -c "import gdbm"`` and other similar
  commands at install time; the exact list is in 
  :source:`pypy/tool/release/package.py <package.py>`.  Users
  seeing a broken installation of PyPy can fix it after-the-fact if they
  have sudo rights, by running once e.g. ``sudo pypy -c "import gdbm``.

* PyPy 2.6 and later: anyone would get ``ImportError: no module named
  _gdbm_cffi``.  Installers need to run ``pypy _gdbm_build.py`` in the
  ``lib_pypy`` directory during the installation process (plus others;
  see the exact list in :source:`pypy/tool/release/package.py <package.py>`).
  Users seeing a broken
  installation of PyPy can fix it after-the-fact, by running ``pypy
  /path/to/lib_pypy/_gdbm_build.py``.  This command produces a file
  called ``_gdbm_cffi.pypy-41.so`` locally, which is a C extension
  module for PyPy.  You can move it at any place where modules are
  normally found: e.g. in your project's main directory, or in a
  directory that you add to the env var ``PYTHONPATH``.


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
