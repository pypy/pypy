===============
PyPy on Windows
===============

Pypy is supported on Windows platforms, starting with Windows 2000.
The following text gives some hints about how to translate the PyPy
interpreter.

To build pypy-c you need a C compiler.  Microsoft Visual Studio is
preferred, but can also use the mingw32 port of gcc.


Translating PyPy with Visual Studio
-----------------------------------

We routinely test the `RPython translation toolchain`_ using Visual Studio .NET
2005, Professional Edition, and Visual Studio .NET 2008, Express
Edition.  Other configurations may work as well.

The translation scripts will set up the appropriate environment variables
for the compiler.  They will attempt to locate the same compiler version that
was used to build the Python interpreter doing the
translation.  Failing that, they will pick the most recent Visual Studio
compiler they can find.  In addition, the target architecture
(32 bits, 64 bits) is automatically selected.  A 32 bit build can only be built
using a 32 bit Python and vice versa.

**Note:** PyPy is currently not supported for 64 bit Windows, and translation
will be aborted in this case.

The compiler is all you need to build pypy-c, but it will miss some
modules that relies on third-party libraries.  See below how to get
and build them.

Preping Windows for the Large Build
-----------------------------------

Follow http://usa.autodesk.com/adsk/servlet/ps/dl/item?siteID=123112&id=9583842&linkID=9240617
to allow Windows up to 3GB for 32bit applications if you are on a
32bit version of windows. If you are using Visual C++ 2008 (untested
with 2005), then you will have a utility called editbin.exe within
Visual Studio 9.0\VC\bin. You will need to execute::

    editbin /largeaddressaware pypy.exe

on the pypy.exe or python.exe you are using to buld the new
pypy. Reboot now if you followed the 3G instructions for 32bit
windows.

Installing external packages
----------------------------

On Windows, there is no standard place where to download, build and
install third-party libraries.  We chose to install them in the parent
directory of the pypy checkout.  For example, if you installed pypy in
``d:\pypy\trunk\`` (This directory contains a README file), the base
directory is ``d:\pypy``.

The Boehm garbage collector
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This library is needed if you plan to use the ``--gc=boehm`` translation
option (this is the default at some optimization levels like ``-O1``,
but unneeded for high-performance translations like ``-O2``).
You may get it at
http://www.hpl.hp.com/personal/Hans_Boehm/gc/gc_source/gc-7.1.tar.gz

Versions 7.0 and 7.1 are known to work; the 6.x series won't work with
pypy. Unpack this folder in the base directory.  Then open a command
prompt::

    cd gc-7.1
    nmake -f NT_THREADS_MAKEFILE
    copy Release\gc.dll <somewhere in the PATH>

The zlib compression library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download http://www.gzip.org/zlib/zlib-1.2.3.tar.gz and extract it in
the base directory.  Then compile::

    cd zlib-1.2.3
    nmake -f win32\Makefile.msc
    copy zlib1.dll <somewhere in the PATH>\zlib.dll

The bz2 compression library
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download http://bzip.org/1.0.5/bzip2-1.0.5.tar.gz and extract it in
the base directory.  Then compile::

    cd bzip2-1.0.5
    nmake -f makefile.msc
    
The expat XML parser
~~~~~~~~~~~~~~~~~~~~

Download the source code of expat on sourceforge:
http://sourceforge.net/projects/expat/ and extract it in the base
directory.  Then open the project file ``expat.dsw`` with Visual
Studio; follow the instruction for converting the project files,
switch to the "Release" configuration, and build the solution (the
``expat`` project is actually enough for pypy).

Then, copy the file ``win32\bin\release\libexpat.dll`` somewhere in
your PATH.

The OpenSSL library
~~~~~~~~~~~~~~~~~~~

OpenSSL needs a Perl interpreter to configure its makefile.  You may
use the one distributed by ActiveState, or the one from cygwin.  In
both case the perl interpreter must be found on the PATH.

Get http://www.openssl.org/source/openssl-0.9.8k.tar.gz and extract it
in the base directory. Then compile::

    perl Configure VC-WIN32
    ms\do_ms.bat
    nmake -f ms\nt.mak install

Using the mingw compiler
------------------------

You can compile pypy with the mingw compiler, using the --cc=mingw32 option;
mingw.exe must be on the PATH.

libffi for the mingw32 compiler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable the _rawffi (and ctypes) module, you need to compile a mingw32
version of libffi.  I downloaded the `libffi source files`_, and extracted
them in the base directory.  Then run::

    sh ./configure
    make
    cp .libs/libffi-5.dll <somewhere on the PATH>

.. _`libffi source files`: http://sourceware.org/libffi/
.. _`RPython translation toolchain`: translation.html
