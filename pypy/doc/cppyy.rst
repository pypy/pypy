============================
cppyy: C++ bindings for pypy
============================

The cppyy module provides C++ bindings for PyPy by using the reflection
information extracted from C++ header files by means of the
`Reflex package`_.
For this to work, you have to both install Reflex and build PyPy from the
reflex-support branch.
As indicated by this being a branch, support for Reflex is still
experimental.
However, it is functional enough to put it in the hands of those who want
to give it a try.
In the medium term, cppyy will move away from Reflex and instead use
`cling`_ as its backend, which is based on `llvm`_.
Although that will change the logistics on the generation of reflection
information, it will not change the python-side interface.

.. _`Reflex package`: http://root.cern.ch/drupal/content/reflex
.. _`cling`: http://root.cern.ch/drupal/content/cling
.. _`llvm`: http://llvm.org/


Installation
============

For now, the easiest way of getting the latest version of Reflex, is by
installing the ROOT package.
`Download`_ a binary or install from `source`_.
Some Linux and Mac systems may have ROOT provided in the list of scientific
software of their packager.
A current, standalone version of Reflex should be provided at some point,
once the dependencies and general packaging have been thought out.
Also, make sure you have a version of `gccxml`_ installed, which is most
easily provided by the packager of your system.
If you read up on gccxml, you'll probably notice that it is no longer being
developed and hence will not provide C++11 support.
That's why the medium plan is to move to `cling`_.

.. _`Download`: http://root.cern.ch/drupal/content/downloading-root
.. _`source`: http://root.cern.ch/drupal/content/installing-root-source
.. _`gccxml`: http://www.gccxml.org

Next, get the `PyPy sources`_, select the reflex-support branch, and build
pypy-c.
For the build to succeed, the ``$ROOTSYS`` environment variable must point to
the location of your ROOT installation::

    $ hg clone https://bitbucket.org/pypy/pypy
    $ cd pypy
    $ hg up reflex-support
    $ cd pypy/translator/goal
    $ python translate.py -O jit --gcrootfinder=shadowstack targetpypystandalone.py --withmod-cppyy

This will build a ``pypy-c`` that includes the cppyy module, and through that,
Reflex support.
Of course, if you already have a prebuilt version of the ``pypy`` interpreter,
you can use that for the translation rather than ``python``.

.. _`PyPy sources`: https://bitbucket.org/pypy/pypy/overview


Basic example
=============

Now test with a trivial example whether all packages are properly installed
and functional.
First, create a C++ header file with some class in it (note that all functions
are made inline for convenience; a real-world example would of course have a
corresponding source file)::

    $ cat MyClass.h
    class MyClass {
    public:
        MyClass( int i = -99) : m_myint( i ) {}

        int GetMyInt() { return m_myint; }
        void SetMyInt( int i ) { m_myint = i; }

    public:
       int m_myint;
    };

Then, generate the bindings using ``genreflex`` (part of ROOT), and compile the
code::

    $ genreflex MyClass.h
    $ g++ -fPIC -rdynamic -O2 -shared -I$ROOTSYS/include MyClass_rflx.cpp -o libMyClassDict.so

Now you're ready to use the bindings.
Since the bindings are designed to look pythonistic, it should be
straightforward::

    $ pypy-c
    >>>> import cppyy
    >>>> cppyy.load_reflection_info("libMyClassDict.so")
    <CPPLibrary object at 0xb6fd7c4c>
    >>>> myinst = cppyy.gbl.MyClass(42)
    >>>> print myinst.GetMyInt()
    42
    >>>> myinst.SetMyInt(33)
    >>>> print myinst.m_myint
    33
    >>>> myinst.m_myint = 77
    >>>> print myinst.GetMyInt()
    77
    >>>> help(cppyy.gbl.MyClass)   # shows that normal python introspection works

That's all there is to it!
