==============================================
Getting Started with PyPy's Python Interpreter
==============================================

.. contents::


PyPy's Python interpreter is a very compliant Python
interpreter implemented in Python.  When translated to C, it passes most of 
`CPythons core language regression tests`_ and comes with many of the extension
modules included in the standard library including ``ctypes``. It can run large
libraries such as Django_ and Twisted_. There are some small behavioral
differences with CPython and some missing extensions, for details see `CPython
differences`_.

.. _Django: http://djangoproject.com
.. _Twisted: http://twistedmatrix.com

.. _`CPython differences`: cpython_differences.html

To actually use PyPy's Python interpreter, the first thing to do is to 
`download a pre-built PyPy`_ for your architecture.  

.. _`download a pre-built PyPy`:  http://pypy.org/download.html

Translating the PyPy Python interpreter
---------------------------------------

(**Note**: for some hints on how to translate the Python interpreter under
Windows, see the `windows document`_)

.. _`windows document`: windows.html

You can translate the whole of PyPy's Python interpreter to low level C code,
or `CLI code`_.

1. First `download a pre-built PyPy`_ for your architecture which you will
   use to translate your Python interpreter.  It is, of course, possible to
   translate with a CPython 2.6 or later, but this is not the preferred way,
   because it will take a lot longer to run -- depending on your architecture,
   between two and three times as long.

2. Install build-time dependencies.  On a Debian box these are::

     [user@debian-box ~]$ sudo apt-get install \
     gcc make python-dev libffi-dev pkg-config \
     libz-dev libbz2-dev libncurses-dev libexpat1-dev \
     libssl-dev libgc-dev python-sphinx python-greenlet

   On a Fedora box these are::

     [user@fedora-or-rh-box ~]$ sudo yum install \
     gcc make python-devel libffi-devel pkg-config \
     zlib-devel bzip2-devel ncurses-devel expat-devel \
     openssl-devel gc-devel python-sphinx python-greenlet

   The above command lines are split with continuation characters, giving the necessary dependencies first, then the optional ones.

   * ``pkg-config`` (to help us locate libffi files)
   * ``libz-dev`` (for the optional ``zlib`` module)
   * ``libbz2-dev`` (for the optional ``bz2`` module)
   * ``libncurses-dev`` (for the optional ``_minimal_curses`` module)
   * ``libexpat1-dev`` (for the optional ``pyexpat`` module)
   * ``libssl-dev`` (for the optional ``_ssl`` module)
   * ``libgc-dev`` (for the Boehm garbage collector: only needed when translating with `--opt=0, 1` or `size`)
   * ``python-sphinx`` (for the optional documentation build.  You need version 1.0.7 or later)
   * ``python-greenlet`` (for the optional stackless support in interpreted mode/testing)


3. Translation is time-consuming -- 45 minutes on a very fast machine --
   and RAM-hungry.  As of March 2011, you will need **at least** 2 GB of 
   memory on a 
   32-bit machine and 4GB on a 64-bit machine.  If your memory resources 
   are constrained, or your machine is slow you might want to pick the
   `optimization level`_ `1` in the next step.  A level of
   `2` or `3` or `jit` gives much better results, though.  But if all
   you want to do is to test that some new feature that you just wrote
   translates, level 1 is enough.

   Let me stress this again: at ``--opt=1`` you get the Boehm
   GC, which is here mostly for historical and for testing reasons.
   You really do not want to pick it for a program you intend to use.  
   The resulting ``pypy-c`` is slow.

4. Run::

     cd pypy/translator/goal
     python translate.py --opt=jit targetpypystandalone.py

   possibly replacing ``--opt=jit`` with another `optimization level`_
   of your choice like ``--opt=2`` if you do not want to include the JIT
   compiler, which makes the Python interpreter much slower.  

.. _`optimization level`: config/opt.html

If everything works correctly this will create an executable
``pypy-c`` in the current directory.  Type ``pypy-c --help``
to see the options it supports - mainly the same basic
options as CPython.  In addition, ``pypy-c --info`` prints the
translation options that where used to produce this particular
executable. The executable behaves mostly like a normal Python interpreter::

    $ ./pypy-c
    Python 2.7.0 (61ef2a11b56a, Mar 02 2011, 03:00:11)
    [PyPy 1.5.0-alpha0 with GCC 4.4.3] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    And now for something completely different: ``this sentence is false''
    >>>> 46 - 4
    42
    >>>> from test import pystone
    >>>> pystone.main()
    Pystone(1.1) time for 50000 passes = 0.280017
    This machine benchmarks at 178561 pystones/second
    >>>>

This executable can be moved around or copied on other machines; see
Installation_ below.

The ``translate.py`` script takes a very large number of options controlling
what to translate and how.  See ``translate.py -h``. Some of the more
interesting options (but for now incompatible with the JIT) are:

   * ``--stackless``: this produces a pypy-c that includes features
     inspired by `Stackless Python <http://www.stackless.com>`__.

   * ``--gc=boehm|ref|marknsweep|semispace|generation|hybrid|minimark``:
     choose between using
     the `Boehm-Demers-Weiser garbage collector`_, our reference
     counting implementation or one of own collector implementations
     (the default depends on the optimization level but is usually
     ``minimark``).

Find a more detailed description of the various options in our `configuration
sections`_.

.. _`configuration sections`: config/index.html

.. _`translate PyPy with the thunk object space`:

Translating with non-standard options
++++++++++++++++++++++++++++++++++++++++

It is possible to have non-standard features enabled for translation,
but they are not really tested any more.  Look, for example, at the
`objspace proxies`_ document.

.. _`objspace proxies`: objspace-proxies.html

.. _`CLI code`: 

Translating using the CLI backend
+++++++++++++++++++++++++++++++++

To create a standalone .NET executable using the `CLI backend`_::

    ./translate.py --backend=cli targetpypystandalone.py

The executable and all its dependencies will be stored in the
./pypy-cli-data directory. To run pypy.NET, you can run
./pypy-cli-data/main.exe. If you are using Linux or Mac, you can use
the convenience ./pypy-cli script::

    $ ./pypy-cli
    Python 2.7.0 (61ef2a11b56a, Mar 02 2011, 03:00:11)
    [PyPy 1.5.0-alpha0] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    And now for something completely different: ``distopian and utopian chairs''
    >>>> 

Moreover, at the moment it's not possible to do the full translation
using only the tools provided by the Microsoft .NET SDK, since
``ilasm`` crashes when trying to assemble the pypy-cli code due to its
size.  Microsoft .NET SDK 2.0.50727.42 is affected by this bug; other
versions could be affected as well: if you find a version of the SDK
that works, please tell us.

Windows users that want to compile their own pypy-cli can install
Mono_: if a Mono installation is detected the translation toolchain
will automatically use its ``ilasm2`` tool to assemble the
executables.

To try out the experimental .NET integration, check the documentation of the
clr_ module.

..  not working now:

    .. _`JVM code`: 

    Translating using the JVM backend
    +++++++++++++++++++++++++++++++++

    To create a standalone JVM executable::

        ./translate.py --backend=jvm targetpypystandalone.py

    This will create a jar file ``pypy-jvm.jar`` as well as a convenience
    script ``pypy-jvm`` for executing it.  To try it out, simply run
    ``./pypy-jvm``::

        $ ./pypy-jvm 
        Python 2.7.0 (61ef2a11b56a, Mar 02 2011, 03:00:11)
        [PyPy 1.5.0-alpha0] on linux2
        Type "help", "copyright", "credits" or "license" for more information.
        And now for something completely different: ``# assert did not crash''
        >>>> 

    Alternatively, you can run it using ``java -jar pypy-jvm.jar``. At the moment
    the executable does not provide any interesting features, like integration with
    Java.

Installation
++++++++++++

A prebuilt ``pypy-c`` can be installed in a standard location like
``/usr/local/bin``, although some details of this process are still in
flux.  It can also be copied to other machines as long as their system
is "similar enough": some details of the system on which the translation
occurred might be hard-coded in the executable.

PyPy dynamically finds the location of its libraries depending on the location
of the executable.  The directory hierarchy of a typical PyPy installation
looks like this::

   ./bin/pypy
   ./include/
   ./lib_pypy/
   ./lib-python/2.7
   ./lib-python/modified-2.7
   ./site-packages/

The hierarchy shown above is relative to a PREFIX directory.  PREFIX is
computed by starting from the directory where the executable resides, and
"walking up" the filesystem until we find a directory containing ``lib_pypy``,
``lib-python/2.7`` and ``lib-python/2.7.1``.

The archives (.tar.bz2 or .zip) containing PyPy releases already contain the
correct hierarchy, so to run PyPy it's enough to unpack the archive, and run
the ``bin/pypy`` executable.

To install PyPy system wide on unix-like systems, it is recommended to put the
whole hierarchy alone (e.g. in ``/opt/pypy1.5``) and put a symlink to the
``pypy`` executable into ``/usr/bin`` or ``/usr/local/bin``

If the executable fails to find suitable libraries, it will report
``debug: WARNING: library path not found, using compiled-in sys.path``
and then attempt to continue normally.  If the default path is usable,
most code will be fine.  However, the ``sys.prefix`` will be unset
and some existing libraries assume that this is never the case.

.. _`py.py interpreter`:

Running the Python Interpreter Without Translation
---------------------------------------------------

The py.py interpreter
+++++++++++++++++++++

To start interpreting Python with PyPy, install a C compiler that is
supported by distutils and use Python 2.5 or greater to run PyPy::

    cd pypy
    python bin/py.py

After a few seconds (remember: this is running on top of CPython), 
you should be at the PyPy prompt, which is the same as the Python 
prompt, but with an extra ">".

Now you are ready to start running Python code.  Most Python
modules should work if they don't involve CPython extension 
modules.  **This is slow, and most C modules are not present by
default even if they are standard!**  Here is an example of
determining PyPy's performance in pystones:: 

    >>>> from test import pystone 
    >>>> pystone.main(10)

The parameter is the number of loops to run through the test. The
default is 50000, which is far too many to run in a non-translated
PyPy version (i.e. when PyPy's interpreter itself is being interpreted 
by CPython).

py.py options
+++++++++++++

To list the PyPy interpreter command line options, type::

    cd pypy
    python bin/py.py --help

py.py supports most of the options that CPython supports too (in addition to a
large amount of options that can be used to customize py.py).
As an example of using PyPy from the command line, you could type::

    python py.py -c "from test import pystone; pystone.main(10)"

Alternatively, as with regular Python, you can simply give a
script name on the command line::

    python py.py ../../lib-python/2.7/test/pystone.py 10

See our  `configuration sections`_ for details about what all the commandline
options do.


.. _Mono: http://www.mono-project.com/Main_Page
.. _`CLI backend`: cli-backend.html
.. _`Boehm-Demers-Weiser garbage collector`: http://www.hpl.hp.com/personal/Hans_Boehm/gc/
.. _clr: clr-module.html
.. _`CPythons core language regression tests`: http://buildbot.pypy.org/summary?category=applevel&branch=%3Ctrunk%3E

.. include:: _ref.txt
