Translating on Windows
======================

RPython is supported on Windows platforms, starting with Windows 2000.
The following text gives some hints about how to translate a interpreter
written in RPython, using PyPy as an example.

PyPy supports only being translated as a 32bit program, even on
64bit Windows.  See at the end of this page for what is missing
for a full 64bit translation.

To build pypy-c you need a working python environment, and a C compiler.
It is possible to translate with a CPython 2.6 or later, but this is not
the preferred way, because it will take a lot longer to run – depending
on your architecture, between two and three times as long. So head to
`our downloads`_ and get the latest stable version.

Microsoft Visual Studio is preferred as a compiler, but there are reports
of success with the mingw32 port of gcc.

.. _our downloads: http://pypy.org/download.html

Installing Visual Compiler v9 (for Python 2.7)
----------------------------------------------

This compiler, while the standard one for Python 2.7, is deprecated. Microsoft has
made it available as the `Microsoft Visual C++ Compiler for Python 2.7`_ (the link
was checked in Nov 2016). Note that the compiler suite may be installed in
``C:\Users\<user name>\AppData\Local\Programs\Common\Microsoft\Visual C++ for Python``
or in
``C:\Program Files (x86)\Common Files\Microsoft\Visual C++ for Python``.
A current version of ``setuptools`` will be able to find it there. For
Windows 10, you must right-click the download, and under ``Properties`` ->
``Compatibility`` mark it as ``Run run this program in comatibility mode for``
``Previous version...``. Also, you must download and install the ``.Net Framework 3.5``,
otherwise ``mt.exe`` will silently fail. Installation will begin automatically
by running the mt.exe command by hand from a DOS window (that is how the author
discovered the problem).

.. _Microsoft Visual C++ Compiler for Python 2.7: https://www.microsoft.com/en-us/download/details.aspx?id=44266

Installing "Build Tools for Visual Studio 2017" (for Python 3)
--------------------------------------------------------------

As documented in the CPython Wiki_, CPython now recommends Visual C++ version
14.0. A compact version of the compiler suite can be obtained from Microsoft_
downloads, search the page for "Build Tools for Visual Studio 2017".

You will also need to install the the `Windows SDK`_ in order to use the 
`mt.exe` mainfest compiler.

.. _Wiki: https://wiki.python.org/moin/WindowsCompilers
.. _Microsoft: https://www.visualstudio.com/downloads
.. _`Windows SDK`: https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk

Translating PyPy with Visual Studio
-----------------------------------

We routinely test translation of PyPy 2.7 using v9 and PyPy 3 with vc14.
Other configurations may work as well.

The translation scripts will set up the appropriate environment variables
for the compiler, so you do not need to run vcvars before translation.
They will attempt to locate the same compiler version that
was used to build the Python interpreter doing the
translation.  Failing that, they will pick the most recent Visual Studio
compiler they can find.  In addition, the target architecture
(32 bits, 64 bits) is automatically selected.  A 32 bit build can only be built
using a 32 bit Python and vice versa. By default the interpreter is built using
the Multi-threaded DLL (/MD) runtime environment.

If you wish to override this detection method to use a different compiler
(mingw or a different version of MSVC):

* set up the PATH and other environment variables as needed
* set the `CC` environment variable to compiler exe to be used,
  for a different version of MSVC `SET CC=cl.exe`.

**Note:** The RPython translator does currently not support 64 bit Python, and
translation will fail in this case.

Python and a C compiler are all you need to build pypy, but it will miss some
modules that relies on third-party libraries.  See below how to get
and build them.

Please see the :doc:`non-windows instructions <build>` for more information, especially note
that translation is RAM-hungry. A standard translation requires around 4GB, so
special preparations are necessary, or you may want to use the method in the
notes of the `build instructions`_ to reduce memory usage at the price of a
slower translation::

    set PYPY_GC_MAX_DELTA=200MB
    pypy --jit loop_longevity=300 ../../rpython/bin/rpython -Ojit targetpypystandalone
    set PYPY_GC_MAX_DELTA=
    PYTHONPATH=../.. ./pypy-c ../tool/build_cffi_imports.py

.. _build instructions: http://pypy.org/download.html#building-from-source

Setting Up Visual Studio 9.0 for building SSL in Python3
--------------------------------------------------------

On Python3, the ``ssl`` module is based on ``cffi``, and requires a build step after
translation. However ``distutils`` does not support the Micorosft-provided Visual C
compiler, and ``cffi`` depends on ``distutils`` to find the compiler. The
traditional solution to this problem is to install the ``setuptools`` module
via running ``-m ensurepip`` which installs ``pip`` and ``setuptools``. However
``pip`` requires ``ssl``. So we have a chicken-and-egg problem: ``ssl`` depends on
``cffi`` which depends on ``setuptools``, which depends on ``ensurepip``, which
depends on ``ssl``.

In order to solve this, the buildbot sets an environment varaible that helps
``distutils`` find the compiler without ``setuptools``::

     set VS90COMNTOOLS=C:\Program Files (x86)\Common Files\Microsoft\Visual C++ for Python\9.0\VC\bin

or whatever is appropriate for your machine. Note that this is not enough, you
must also copy the ``vcvarsall.bat`` file fron the ``...\9.0`` directory to the
``...\9.0\VC`` directory, and edit it, changing the lines that set
``VCINSTALLDIR`` and ``WindowsSdkDir``::

    set VCINSTALLDIR=%~dp0\
    set WindowsSdkDir=%~dp0\..\WinSDK\


Preparing Windows for the large build
-------------------------------------

Normally 32bit programs are limited to 2GB of memory on Windows. It is
possible to raise this limit, to 3GB on Windows 32bit, and almost 4GB
on Windows 64bit.

On Windows 32bit, it is necessary to modify the system: follow
http://usa.autodesk.com/adsk/servlet/ps/dl/item?siteID=123112&id=9583842&linkID=9240617
to enable the "3GB" feature, and reboot. This step is not necessary on
Windows 64bit.

Then you need to execute::

    <path-to-visual>\vc\vcvars.bat
    editbin /largeaddressaware translator.exe

where ``translator.exe`` is the pypy.exe or cpython.exe you will use to
translate with.


Installing external packages
----------------------------

We uses a `repository` parallel to pypy to hold binary compiled versions of the
build dependencies for windows. As part of the `rpython` setup stage, environment
variables will be set to use these dependencies. The repository has a README
file on how to replicate, and a branch for each supported platform. You may run
 the `get_externals.py` utility to checkout the proper branch for your platform
and PyPy version.

.. _repository:  https://bitbucket.org/pypy/external

Using the mingw compiler
------------------------

You can compile an RPython program with the mingw compiler, using the
--cc=mingw32 option; gcc.exe must be on the PATH. If the -cc flag does not
begin with "ming", it should be the name of a valid gcc-derivative compiler,
i.e. x86_64-w64-mingw32-gcc for the 64 bit compiler creating a 64 bit target.

You probably want to set the CPATH, LIBRARY_PATH, and PATH environment
variables to the header files, lib or dlls, and dlls respectively of the
locally installed packages if they are not in the mingw directory heirarchy.


libffi for the mingw compiler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable the _rawffi (and ctypes) module, you need to compile a mingw
version of libffi.  Here is one way to do this, wich should allow you to try
to build for win64 or win32:

#. Download and unzip a `mingw32 build`_ or `mingw64 build`_, say into c:\mingw
#. If you do not use cygwin, you will need msys to provide make,
   autoconf tools and other goodies.

    #. Download and unzip a `msys for mingw`_, say into c:\msys
    #. Edit the c:\msys\etc\fstab file to mount c:\mingw

#. Download and unzip the `libffi source files`_, and extract
   them in the base directory.
#. Run c:\msys\msys.bat or a cygwin shell which should make you
   feel better since it is a shell prompt with shell tools.
#. From inside the shell, cd to the libffi directory and do::

    sh ./configure
    make
    cp .libs/libffi-5.dll <somewhere on the PATH>

If you can't find the dll, and the libtool issued a warning about
"undefined symbols not allowed", you will need to edit the libffi
Makefile in the toplevel directory. Add the flag -no-undefined to
the definition of libffi_la_LDFLAGS

If you wish to experiment with win64, you must run configure with flags::

    sh ./configure --build=x86_64-w64-mingw32 --host=x86_64-w64-mingw32

or such, depending on your mingw64 download.


hacking on PyPy with the mingw compiler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Since hacking on PyPy means running tests, you will need a way to specify
the mingw compiler when hacking (as opposed to translating). As of
March 2012, --cc is not a valid option for pytest.py. However if you set an
environment variable CC to the compiler exe, testing will use it.

.. _mingw32 build: http://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win32/Automated%20Builds
.. _mingw64 build: http://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Automated%20Builds
.. _msys for mingw: http://sourceforge.net/projects/mingw-w64/files/External%20binary%20packages%20%28Win64%20hosted%29/MSYS%20%2832-bit%29
.. _libffi source files: http://sourceware.org/libffi/


What is missing for a full 64-bit translation
---------------------------------------------

The main blocker is that we assume that the integer type of RPython is
large enough to (occasionally) contain a pointer value cast to an
integer.  The simplest fix is to make sure that it is so, but it will
give the following incompatibility between CPython and PyPy on Win64:

CPython: ``sys.maxint == 2**31-1, sys.maxsize == 2**63-1``

PyPy: ``sys.maxint == sys.maxsize == 2**63-1``

...and, correspondingly, PyPy supports ints up to the larger value of
sys.maxint before they are converted to ``long``.  The first decision
that someone needs to make is if this incompatibility is reasonable.

Assuming that it is, the first thing to do is probably to hack *CPython*
until it fits this model: replace the field in PyIntObject with a ``long
long`` field, and change the value of ``sys.maxint``.  This might just
work, even if half-brokenly: I'm sure you can crash it because of the
precision loss that undoubtedly occurs everywhere, but try not to. :-)

Such a hacked CPython is what you'll use in the next steps.  We'll call
it CPython64/64.

It is probably not too much work if the goal is only to get a translated
PyPy executable, and to run all tests before translation.  But you need
to start somewhere, and you should start with some tests in
``rpython/translator/c/test/``, like ``test_standalone.py`` and
``test_newgc.py``: try to have them pass on top of CPython64/64.

Keep in mind that this runs small translations, and some details may go
wrong.  The most obvious one is to check that it produces C files that
use the integer type ``Signed`` --- but what is ``Signed`` defined to?
It should be equal to ``long`` on every other platform, but on Win64 it
should be something like ``long long``.

What is more generally needed is to review all the C files in
``rpython/translator/c/src`` for the word ``long``, because this means a
32-bit integer even on Win64.  Replace it with ``Signed`` most of the
times.  You can replace one with the other without breaking anything on
any other platform, so feel free to.

Then, these two C types have corresponding RPython types: ``rffi.LONG``
and ``lltype.Signed`` respectively.  The first should really correspond
to the C ``long``.  Add tests that check that integers cast to one
type or the other really have 32 and 64 bits respectively, on Win64.

Once these basic tests work, you need to review ``rpython/rlib/`` for
uses of ``rffi.LONG`` versus ``lltype.Signed``.  The goal would be to
fix some more ``LONG-versus-Signed`` issues, by fixing the tests --- as
always run on top of CPython64/64.  Note that there was some early work
done in ``rpython/rlib/rarithmetic`` with the goal of running all the
tests on Win64 on the regular CPython, but I think by now that it's a
bad idea.  Look only at CPython64/64.

The major intermediate goal is to get a translation of PyPy with ``-O2``
with a minimal set of modules, starting with ``--no-allworkingmodules``;
you need to use CPython64/64 to run this translation too.  Check
carefully the warnings of the C compiler at the end. By default, MSVC
reports a lot of mismatches of integer sizes as warnings instead of
errors.

Then you need to review ``pypy/module/*/`` for ``LONG-versus-Signed``
issues.  At some time during this review, we get a working translated
PyPy on Windows 64 that includes all ``--translationmodules``, i.e.
everything needed to run translations.  Once we have that, the hacked
CPython64/64 becomes much less important, because we can run future
translations on top of this translated PyPy.  As soon as we get there,
please *distribute* the translated PyPy.  It's an essential component
for anyone else that wants to work on Win64!  We end up with a strange
kind of dependency --- we need a translated PyPy in order to translate a
PyPy ---, but I believe it's ok here, as Windows executables are
supposed to never be broken by newer versions of Windows.

Happy hacking :-)
