============================
cppyy: C++ bindings for PyPy
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
Besides getting the latest version of Reflex, another advantage is that with
the full ROOT package, you can also use your Reflex-bound code on `CPython`_.
`Download`_ a binary or install from `source`_.
Some Linux and Mac systems may have ROOT provided in the list of scientific
software of their packager.
A current, standalone version of Reflex should be provided at some point,
once the dependencies and general packaging have been thought out.
Also, make sure you have a version of `gccxml`_ installed, which is most
easily provided by the packager of your system.
If you read up on gccxml, you'll probably notice that it is no longer being
developed and hence will not provide C++11 support.
That's why the medium term plan is to move to `cling`_.

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
Of course, if you already have a pre-built version of the ``pypy`` interpreter,
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
        MyClass(int i = -99) : m_myint(i) {}

        int GetMyInt() { return m_myint; }
        void SetMyInt(int i) { m_myint = i; }

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


Advanced example
================
The following snippet of C++ is very contrived, to allow showing that such
pathological code can be handled and to show how certain features play out in
practice::

    $ cat MyAdvanced.h
    #include <string>

    class Base1 {
    public:
        Base1(int i) : m_i(i) {}
        virtual ~Base1() {}
        int m_i;
    };

    class Base2 {
    public:
        Base2(double d) : m_d(d) {}
        virtual ~Base2() {}
        double m_d;
    };

    class C;

    class Derived : public virtual Base1, public virtual Base2 {
    public:
        Derived(const std::string& name, int i, double d) : Base1(i), Base2(d), m_name(name) {}
        virtual C* gimeC() { return (C*)0; }
        std::string m_name;
    };

    Base1* BaseFactory(const std::string& name, int i, double d) {
        return new Derived(name, i, d);
    }

This code is still only in a header file, with all functions inline, for
convenience of the example.
If the implementations live in a separate source file or shared library, the
only change needed is to link those in when building the reflection library.

If you were to run ``genreflex`` like above in the basic example, you will
find that not all classes of interest will be reflected, nor will be the
global factory function.
In particular, ``std::string`` will be missing, since it is not defined in
this header file, but in a header file that is included.
In practical terms, general classes such as ``std::string`` should live in a
core reflection set, but for the moment assume we want to have it in the
reflection library that we are building for this example.

The ``genreflex`` script can be steered using a so-called `selection file`_,
which is a simple XML file specifying, either explicitly or by using a
pattern, which classes, variables, namespaces, etc. to select from the given
header file.
With the aid of a selection file, a large project can be easily managed:
simply ``#include`` all relevant headers into a single header file that is
handed to ``genreflex``.
Then, apply a selection file to pick up all the relevant classes.
For our purposes, the following rather straightforward selection will do
(the name ``lcgdict`` for the root is historical, but required)::

    $ cat MyAdvanced.xml
    <lcgdict>
       <class pattern="Base?" />
       <class name="Derived" />
       <class name="std::string" />
       <function name="BaseFactory" />
    </lcgdict>

.. _`selection file`: http://root.cern.ch/drupal/content/generating-reflex-dictionaries

Now the reflection info can be generated and compiled::

    $ genreflex MyAdvanced.h --selection=MyAdvanced.xml
    $ g++ -fPIC -rdynamic -O2 -shared -I$ROOTSYS/include MyAdvanced_rflx.cpp -o libAdvExDict.so

and subsequently be used from PyPy::

    >>>> import cppyy
    >>>> cppyy.load_reflection_info("libAdvExDict.so")
    <CPPLibrary object at 0x00007fdb48fc8120>
    >>>> d = cppyy.gbl.BaseFactory("name", 42, 3.14)
    >>>> type(d)
    <class '__main__.Derived'>
    >>>> d.m_i
    42
    >>>> d.m_d
    3.14
    >>>> d.m_name == "name"
    True
    >>>>

Again, that's all there is to it!

A couple of things to note, though.
If you look back at the C++ definition of the ``BaseFactory`` function,
you will see that it declares the return type to be a ``Base1``, yet the
bindings return an object of the actual type ``Derived``?
This choice is made for a couple of reasons.
First, it makes method dispatching easier: if bound objects are always their
most derived type, then it is easy to calculate any offsets, if necessary.
Second, it makes memory management easier: the combination of the type and
the memory address uniquely identifies an object.
That way, it can be recycled and object identity can be maintained if it is
entered as a function argument into C++ and comes back to PyPy as a return
value.
Last, but not least, casting is decidedly unpythonistic.
By always providing the most derived type known, casting becomes unnecessary.
For example, the data member of ``Base2`` is simply directly available.
Note also that the unreflected ``gimeC`` method of ``Derived`` does not
preclude its use.
It is only the ``gimeC`` method that is unusable as long as class ``C`` is
unknown to the system.


Features
========

The following is not meant to be an exhaustive list, since cppyy is still
under active development.
Furthermore, the intention is that every feature is as natural as possible on
the python side, so if you find something missing in the list below, simply
try it out.
It is not always possible to provide exact mapping between python and C++
(active memory management is one such case), but by and large, if the use of a
feature does not strike you as obvious, it is more likely to simply be a bug.
That is a strong statement to make, but also a worthy goal.

* **abstract classes**: Are represented as python classes, since they are
  needed to complete the inheritance hierarchies, but will raise an exception
  if an attempt is made to instantiate from them.

* **arrays**: Supported for builtin data types only, as used from module
  ``array``.
  Out-of-bounds checking is limited to those cases where the size is known at
  compile time (and hence part of the reflection info).

* **builtin data types**: Map onto the expected equivalent python types, with
  the caveat that there may be size differences, and thus it is possible that
  exceptions are raised if an overflow is detected.

* **casting**: Is supposed to be unnecessary.
  Object pointer returns from functions provide the most derived class known
  in the hierarchy of the object being returned.
  This is important to preserve object identity as well as to make casting,
  a pure C++ feature after all, superfluous.

* **classes and structs**: Get mapped onto python classes, where they can be
  instantiated as expected.
  If classes are inner classes or live in a namespace, their naming and
  location will reflect that.

* **data members**: Public data members are represented as python properties
  and provide read and write access on instances as expected.

* **default arguments**: C++ default arguments work as expected, but python
  keywords are not supported.
  It is technically possible to support keywords, but for the C++ interface,
  the formal argument names have no meaning and are not considered part of the
  API, hence it is not a good idea to use keywords.

* **doc strings**: The doc string of a method or function contains the C++
  arguments and return types of all overloads of that name, as applicable.

* **enums**: Are translated as ints with no further checking.

* **functions**: Work as expected and live in their appropriate namespace
  (which can be the global one, ``cppyy.gbl``).

* **inheritance**: All combinations of inheritance on the C++ (single,
  multiple, virtual) are supported in the binding.
  However, new python classes can only use single inheritance from a bound C++
  class.
  Multiple inheritance would introduce two "this" pointers in the binding.
  This is a current, not a fundamental, limitation.
  The C++ side will not see any overridden methods on the python side, as
  cross-inheritance is planned but not yet supported.

* **methods**: Are represented as python methods and work as expected.
  They are first class objects and can be bound to an instance.
  Virtual C++ methods work as expected.
  To select a specific virtual method, do like with normal python classes
  that override methods: select it from the class that you need, rather than
  calling the method on the instance.

* **namespaces**: Are represented as python classes.
  Namespaces are more open-ended than classes, so sometimes initial access may
  result in updates as data and functions are looked up and constructed
  lazily.
  Thus the result of ``dir()`` on a namespace should not be relied upon: it
  only shows the already accessed members. (TODO: to be fixed by implementing
  __dir__.)
  The global namespace is ``cppyy.gbl``.

* **operator conversions**: If defined in the C++ class and a python
  equivalent exists (i.e. all builtin integer and floating point types, as well
  as ``bool``), it will map onto that python conversion.
  Note that ``char*`` is mapped onto ``__str__``.

* **operator overloads**: If defined in the C++ class and if a python
  equivalent is available (not always the case, think e.g. of ``operator||``),
  then they work as expected.
  Special care needs to be taken for global operator overloads in C++: first,
  make sure that they are actually reflected, especially for the global
  overloads for ``operator==`` and ``operator!=`` of STL iterators in the case
  of gcc.
  Second, make sure that reflection info is loaded in the proper order.
  I.e. that these global overloads are available before use.

* **pointers**: For builtin data types, see arrays.
  For objects, a pointer to an object and an object looks the same, unless
  the pointer is a data member.
  In that case, assigning to the data member will cause a copy of the pointer
  and care should be taken about the object's life time.
  If a pointer is a global variable, the C++ side can replace the underlying
  object and the python side will immediately reflect that.

* **static data members**: Are represented as python property objects on the
  class and the meta-class.
  Both read and write access is as expected.

* **static methods**: Are represented as python's ``staticmethod`` objects
  and can be called both from the class as well as from instances.

* **strings**: The std::string class is considered a builtin C++ type and
  mixes quite well with python's str.
  Python's str can be passed where a ``const char*`` is expected, and an str
  will be returned if the return type is ``const char*``.

* **templated classes**: Are represented in a meta-class style in python.
  This looks a little bit confusing, but conceptually is rather natural.
  For example, given the class ``std::vector<int>``, the meta-class part would
  be ``std.vector`` in python.
  Then, to get the instantiation on ``int``, do ``std.vector(int)`` and to
  create an instance of that class, do ``std.vector(int)()``.
  Note that templates can be build up by handing actual types to the class
  instantiation (as done in this vector example), or by passing in the list of
  template arguments as a string.
  The former is a lot easier to work with if you have template instantiations
  using classes that themselves are templates (etc.) in the arguments.
  All classes must already exist in the loaded reflection info.

* **unary operators**: Are supported if a python equivalent exists, and if the
  operator is defined in the C++ class.

You can always find more detailed examples and see the full of supported
features by looking at the tests in pypy/module/cppyy/test.

If a feature or reflection info is missing, this is supposed to be handled
gracefully.
In fact, there are unit tests explicitly for this purpose (even as their use
becomes less interesting over time, as the number of missing features
decreases).
Only when a missing feature is used, should there be an exception.
For example, if no reflection info is available for a return type, then a
class that has a method with that return type can still be used.
Only that one specific method can not be used.


The fast lane
=============

The following is an experimental feature of cppyy, and that makes it doubly
experimental, so caveat emptor.
With a slight modification of Reflex, it can provide function pointers for
C++ methods, and hence allow PyPy to call those pointers directly, rather than
calling C++ through a Reflex stub.
This results in a rather significant speed-up.
Mind you, the normal stub path is not exactly slow, so for now only use this
out of curiosity or if you really need it.

To install this patch of Reflex, locate the file genreflex-methptrgetter.patch
in pypy/module/cppyy and apply it to the genreflex python scripts found in
``$ROOTSYS/lib``::

    $ cd $ROOTSYS/lib
    $ patch -p2 < genreflex-methptrgetter.patch

With this patch, ``genreflex`` will have grown the ``--with-methptrgetter``
option.
Use this option when running ``genreflex``, and add the
``-Wno-pmf-conversions`` option to ``g++`` when compiling.
The rest works the same way: the fast path will be used transparently (which
also means that you can't actually find out whether it is in use, other than
by running a micro-benchmark).


CPython
=======

Most of the ideas in cppyy come originally from the `PyROOT`_ project.
Although PyROOT does not support Reflex directly, it has an alter ego called
"PyCintex" that, in a somewhat roundabout way, does.
If you installed ROOT, rather than just Reflex, PyCintex should be available
immediately if you add ``$ROOTSYS/lib`` to the ``PYTHONPATH`` environment
variable.

.. _`PyROOT`: http://root.cern.ch/drupal/content/pyroot

There are a couple of minor differences between PyCintex and cppyy, most to do
with naming.
The one that you will run into directly, is that PyCintex uses a function
called ``loadDictionary`` rather than ``load_reflection_info``.
The reason for this is that Reflex calls the shared libraries that contain
reflection info "dictionaries."
However, in python, the name `dictionary` already has a well-defined meaning,
so a more descriptive name was chosen for cppyy.
In addition, PyCintex requires that the names of shared libraries so loaded
start with "lib" in their name.
The basic example above, rewritten for PyCintex thus goes like this::

    $ python
    >>> import PyCintex
    >>> PyCintex.loadDictionary("libMyClassDict.so")
    >>> myinst = PyCintex.gbl.MyClass(42)
    >>> print myinst.GetMyInt()
    42
    >>> myinst.SetMyInt(33)
    >>> print myinst.m_myint
    33
    >>> myinst.m_myint = 77
    >>> print myinst.GetMyInt()
    77
    >>> help(PyCintex.gbl.MyClass)   # shows that normal python introspection works

Other naming differences are such things as taking an address of an object.
In PyCintex, this is done with ``AddressOf`` whereas in cppyy the choice was
made to follow the naming as in ``ctypes`` and hence use ``addressof``
(PyROOT/PyCintex predate ``ctypes`` by several years, and the ROOT project
follows camel-case, hence the differences).

Of course, this is python, so if any of the naming is not to your liking, all
you have to do is provide a wrapper script that you import instead of
importing the ``cppyy`` or ``PyCintex`` modules directly.
In that wrapper script you can rename methods exactly the way you need it.

In the cling world, all these differences will be resolved.
