cppyy: C++ bindings for PyPy
============================

The cppyy module delivers dynamic Python-C++ bindings.
It is designed for automation, high performance, scale, interactivity, and
handling all of modern C++ (11, 14, etc.).
It is based on `Cling`_ which, through `LLVM`_/`clang`_, provides C++
reflection and interactivity.
Reflection information is extracted from C++ header files.
Cppyy itself is built into PyPy (an alternative exists for CPython), but
it requires a `backend`_, installable through pip, to interface with Cling.

.. _Cling: https://root.cern.ch/cling
.. _LLVM: http://llvm.org/
.. _clang: http://clang.llvm.org/
.. _backend: https://pypi.python.org/pypi/PyPy-cppyy-backend


Installation
------------

This assumes PyPy2.7 v5.7 or later; earlier versions use a Reflex-based cppyy
module, which is no longer supported.
Both the tooling and user-facing Python codes are very backwards compatible,
however.
Further dependencies are cmake (for general build), Python2.7 (for LLVM), and
a modern C++ compiler (one that supports at least C++11).

Assuming you have a recent enough version of PyPy installed, use pip to
complete the installation of cppyy::

 $ MAKE_NPROCS=4 pypy-c -m pip install --verbose PyPy-cppyy-backend

Set the number of parallel builds ('4' in this example, through the MAKE_NPROCS
environment variable) to a number appropriate for your machine.
The building process may take quite some time as it includes a customized
version of LLVM as part of Cling, which is why --verbose is recommended so that
you can see the build progress.

The default installation will be under
$PYTHONHOME/site-packages/cppyy_backend/lib,
which needs to be added to your dynamic loader path (LD_LIBRARY_PATH).
If you need the dictionary and class map generation tools (used in the examples
below), you need to add $PYTHONHOME/site-packages/cppyy_backend/bin to your
executable path (PATH).


Basic bindings example
----------------------

These examples assume that cppyy_backend is pointed to by the environment
variable CPPYYHOME, and that CPPYYHOME/lib is added to LD_LIBRARY_PATH and
CPPYYHOME/bin to PATH.

Let's first test with a trivial example whether all packages are properly
installed and functional.
Create a C++ header file with some class in it (all functions are made inline
for convenience; if you have out-of-line code, link with it as appropriate)::

    $ cat MyClass.h
    class MyClass {
    public:
        MyClass(int i = -99) : m_myint(i) {}

        int GetMyInt() { return m_myint; }
        void SetMyInt(int i) { m_myint = i; }

    public:
        int m_myint;
    };

Then, generate the bindings using ``genreflex`` (installed under
cppyy_backend/bin in site_packages), and compile the code::

    $ genreflex MyClass.h
    $ g++ -std=c++11 -fPIC -rdynamic -O2 -shared -I$CPPYYHOME/include MyClass_rflx.cpp -o libMyClassDict.so -L$CPPYYHOME/lib -lCling

Next, make sure that the library can be found through the dynamic lookup path
(the ``LD_LIBRARY_PATH`` environment variable on Linux, ``PATH`` on Windows),
for example by adding ".".
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


Automatic class loader
----------------------

There is one big problem in the code above, that prevents its use in a (large
scale) production setting: the explicit loading of the reflection library.
Clearly, if explicit load statements such as these show up in code downstream
from the ``MyClass`` package, then that prevents the ``MyClass`` author from
repackaging or even simply renaming the dictionary library.

The solution is to make use of an automatic class loader, so that downstream
code never has to call ``load_reflection_info()`` directly.
The class loader makes use of so-called rootmap files, which ``genreflex``
can produce.
These files contain the list of available C++ classes and specify the library
that needs to be loaded for their use (as an aside, this listing allows for a
cross-check to see whether reflection info is generated for all classes that
you expect).
By convention, the rootmap files should be located next to the reflection info
libraries, so that they can be found through the normal shared library search
path.
They can be concatenated together, or consist of a single rootmap file per
library.
For example::

    $ genreflex MyClass.h --rootmap=libMyClassDict.rootmap --rootmap-lib=libMyClassDict.so
    $ g++ -std=c++11 -fPIC -rdynamic -O2 -shared -I$CPPYYHOME/include MyClass_rflx.cpp -o libMyClassDict.so -L$CPPYYHOME/lib -lCling

where the first option (``--rootmap``) specifies the output file name, and the
second option (``--rootmap-lib``) the name of the reflection library where
``MyClass`` will live.
It is necessary to provide that name explicitly, since it is only in the
separate linking step where this name is fixed.
If the second option is not given, the library is assumed to be libMyClass.so,
a name that is derived from the name of the header file.

With the rootmap file in place, the above example can be rerun without explicit
loading of the reflection info library::

    $ pypy-c
    >>>> import cppyy
    >>>> myinst = cppyy.gbl.MyClass(42)
    >>>> print myinst.GetMyInt()
    42
    >>>> # etc. ...

As a caveat, note that the class loader is currently limited to classes only.


Advanced example
----------------

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

    Base2* BaseFactory(const std::string& name, int i, double d) {
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

The ``genreflex`` script can be steered using a so-called `selection file`_
(see "Generating Reflex Dictionaries")
which is a simple XML file specifying, either explicitly or by using a
pattern, which classes, variables, namespaces, etc. to select from the given
header file.
With the aid of a selection file, a large project can be easily managed:
simply ``#include`` all relevant headers into a single header file that is
handed to ``genreflex``.
In fact, if you hand multiple header files to ``genreflex``, then a selection
file is almost obligatory: without it, only classes from the last header will
be selected.
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

.. _selection file: https://root.cern.ch/how/how-use-reflex

Now the reflection info can be generated and compiled::

    $ genreflex MyAdvanced.h --selection=MyAdvanced.xml
    $ g++ -std=c++11 -fPIC -rdynamic -O2 -shared -I$CPPYYHOME/include MyAdvanced_rflx.cpp -o libAdvExDict.so -L$CPPYYHOME/lib -lCling

and subsequently be used from PyPy::

    >>>> import cppyy
    >>>> cppyy.load_reflection_info("libAdvExDict.so")
    <CPPLibrary object at 0x00007fdb48fc8120>
    >>>> d = cppyy.gbl.BaseFactory("name", 42, 3.14)
    >>>> type(d)
    <class '__main__.Derived'>
    >>>> isinstance(d, cppyy.gbl.Base1)
    True
    >>>> isinstance(d, cppyy.gbl.Base2)
    True
    >>>> d.m_i, d.m_d
    (42, 3.14)
    >>>> d.m_name == "name"
    True
    >>>>

Again, that's all there is to it!

A couple of things to note, though.
If you look back at the C++ definition of the ``BaseFactory`` function,
you will see that it declares the return type to be a ``Base2``, yet the
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
--------

The following is not meant to be an exhaustive list, since cppyy is still
under active development.
Furthermore, the intention is that every feature is as natural as possible on
the python side, so if you find something missing in the list below, simply
try it out.
It is not always possible to provide exact mapping between python and C++
(active memory management is one such case), but by and large, if the use of a
feature does not strike you as obvious, it is more likely to simply be a bug.
That is a strong statement to make, but also a worthy goal.
For the C++ side of the examples, refer to this :doc:`example code <cppyy_example>`, which was
bound using::

    $ genreflex example.h --deep --rootmap=libexampleDict.rootmap --rootmap-lib=libexampleDict.so
    $ g++ -std=c++11 -fPIC -rdynamic -O2 -shared -I$CPPYYHOME/include example_rflx.cpp -o libexampleDict.so -L$CPPYYHOME/lib -lCling

* **abstract classes**: Are represented as python classes, since they are
  needed to complete the inheritance hierarchies, but will raise an exception
  if an attempt is made to instantiate from them.
  Example::

    >>>> from cppyy.gbl import AbstractClass, ConcreteClass
    >>>> a = AbstractClass()
    Traceback (most recent call last):
      File "<console>", line 1, in <module>
    TypeError: cannot instantiate abstract class 'AbstractClass'
    >>>> issubclass(ConcreteClass, AbstractClass)
    True
    >>>> c = ConcreteClass()
    >>>> isinstance(c, AbstractClass)
    True
    >>>>

* **arrays**: Supported for builtin data types only, as used from module
  ``array``.
  Out-of-bounds checking is limited to those cases where the size is known at
  compile time (and hence part of the reflection info).
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> from array import array
    >>>> c = ConcreteClass()
    >>>> c.array_method(array('d', [1., 2., 3., 4.]), 4)
    1 2 3 4
    >>>>

* **builtin data types**: Map onto the expected equivalent python types, with
  the caveat that there may be size differences, and thus it is possible that
  exceptions are raised if an overflow is detected.

* **casting**: Is supposed to be unnecessary.
  Object pointer returns from functions provide the most derived class known
  in the hierarchy of the object being returned.
  This is important to preserve object identity as well as to make casting,
  a pure C++ feature after all, superfluous.
  Example::

    >>>> from cppyy.gbl import AbstractClass, ConcreteClass
    >>>> c = ConcreteClass()
    >>>> ConcreteClass.show_autocast.__doc__
    'AbstractClass* ConcreteClass::show_autocast()'
    >>>> d = c.show_autocast()
    >>>> type(d)
    <class '__main__.ConcreteClass'>
    >>>>

  However, if need be, you can perform C++-style reinterpret_casts (i.e.
  without taking offsets into account), by taking and rebinding the address
  of an object::

    >>>> from cppyy import addressof, bind_object
    >>>> e = bind_object(addressof(d), AbstractClass)
    >>>> type(e)
    <class '__main__.AbstractClass'>
    >>>>

* **classes and structs**: Get mapped onto python classes, where they can be
  instantiated as expected.
  If classes are inner classes or live in a namespace, their naming and
  location will reflect that.
  Example::

    >>>> from cppyy.gbl import ConcreteClass, Namespace
    >>>> ConcreteClass == Namespace.ConcreteClass
    False
    >>>> n = Namespace.ConcreteClass.NestedClass()
    >>>> type(n)
    <class '__main__.Namespace::ConcreteClass::NestedClass'>
    >>>>

* **data members**: Public data members are represented as python properties
  and provide read and write access on instances as expected.
  Private and protected data members are not accessible.
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> c = ConcreteClass()
    >>>> c.m_int
    42
    >>>>

* **default arguments**: C++ default arguments work as expected, but python
  keywords are not supported.
  It is technically possible to support keywords, but for the C++ interface,
  the formal argument names have no meaning and are not considered part of the
  API, hence it is not a good idea to use keywords.
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> c = ConcreteClass()       # uses default argument
    >>>> c.m_int
    42
    >>>> c = ConcreteClass(13)
    >>>> c.m_int
    13
    >>>>

* **doc strings**: The doc string of a method or function contains the C++
  arguments and return types of all overloads of that name, as applicable.
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> print ConcreteClass.array_method.__doc__
    void ConcreteClass::array_method(int*, int)
    void ConcreteClass::array_method(double*, int)
    >>>>

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
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> help(ConcreteClass)
    Help on class ConcreteClass in module __main__:

    class ConcreteClass(AbstractClass)
     |  Method resolution order:
     |      ConcreteClass
     |      AbstractClass
     |      cppyy.CPPObject
     |      __builtin__.CPPInstance
     |      __builtin__.object
     |
     |  Methods defined here:
     |
     |  ConcreteClass(self, *args)
     |      ConcreteClass::ConcreteClass(const ConcreteClass&)
     |      ConcreteClass::ConcreteClass(int)
     |      ConcreteClass::ConcreteClass()
     |
     etc. ....

* **memory**: C++ instances created by calling their constructor from python
  are owned by python.
  You can check/change the ownership with the _python_owns flag that every
  bound instance carries.
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> c = ConcreteClass()
    >>>> c._python_owns            # True: object created in Python
    True
    >>>>

* **methods**: Are represented as python methods and work as expected.
  They are first class objects and can be bound to an instance.
  Virtual C++ methods work as expected.
  To select a specific virtual method, do like with normal python classes
  that override methods: select it from the class that you need, rather than
  calling the method on the instance.
  To select a specific overload, use the __dispatch__ special function, which
  takes the name of the desired method and its signature (which can be
  obtained from the doc string) as arguments.

* **namespaces**: Are represented as python classes.
  Namespaces are more open-ended than classes, so sometimes initial access may
  result in updates as data and functions are looked up and constructed
  lazily.
  Thus the result of ``dir()`` on a namespace shows the classes available,
  even if they may not have been created yet.
  It does not show classes that could potentially be loaded by the class
  loader.
  Once created, namespaces are registered as modules, to allow importing from
  them.
  Namespace currently do not work with the class loader.
  Fixing these bootstrap problems is on the TODO list.
  The global namespace is ``cppyy.gbl``.

* **NULL**: Is represented as ``cppyy.gbl.nullptr``.
  In C++11, the keyword ``nullptr`` is used to represent ``NULL``.
  For clarity of intent, it is recommended to use this instead of ``None``
  (or the integer ``0``, which can serve in some cases), as ``None`` is better
  understood as ``void`` in C++.

* **operator conversions**: If defined in the C++ class and a python
  equivalent exists (i.e. all builtin integer and floating point types, as well
  as ``bool``), it will map onto that python conversion.
  Note that ``char*`` is mapped onto ``__str__``.
  Example::

    >>>> from cppyy.gbl import ConcreteClass
    >>>> print ConcreteClass()
    Hello operator const char*!
    >>>>

* **operator overloads**: If defined in the C++ class and if a python
  equivalent is available (not always the case, think e.g. of ``operator||``),
  then they work as expected.
  Special care needs to be taken for global operator overloads in C++: first,
  make sure that they are actually reflected, especially for the global
  overloads for ``operator==`` and ``operator!=`` of STL vector iterators in
  the case of gcc (note that they are not needed to iterate over a vector).
  Second, make sure that reflection info is loaded in the proper order.
  I.e. that these global overloads are available before use.

* **pointers**: For builtin data types, see arrays.
  For objects, a pointer to an object and an object looks the same, unless
  the pointer is a data member.
  In that case, assigning to the data member will cause a copy of the pointer
  and care should be taken about the object's life time.
  If a pointer is a global variable, the C++ side can replace the underlying
  object and the python side will immediately reflect that.

* **PyObject***: Arguments and return types of ``PyObject*`` can be used, and
  passed on to CPython API calls.
  Since these CPython-like objects need to be created and tracked (this all
  happens through ``cpyext``) this interface is not particularly fast.

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
  This may look a little bit confusing, but conceptually is rather natural.
  For example, given the class ``std::vector<int>``, the meta-class part would
  be ``std.vector``.
  Then, to get the instantiation on ``int``, do ``std.vector(int)`` and to
  create an instance of that class, do ``std.vector(int)()``::

    >>>> import cppyy
    >>>> cppyy.load_reflection_info('libexampleDict.so')
    >>>> cppyy.gbl.std.vector                # template metatype
    <cppyy.CppyyTemplateType object at 0x00007fcdd330f1a0>
    >>>> cppyy.gbl.std.vector(int)           # instantiates template -> class
    <class '__main__.std::vector<int>'>
    >>>> cppyy.gbl.std.vector(int)()         # instantiates class -> object
    <__main__.std::vector<int> object at 0x00007fe480ba4bc0>
    >>>>

  Note that templates can be build up by handing actual types to the class
  instantiation (as done in this vector example), or by passing in the list of
  template arguments as a string.
  The former is a lot easier to work with if you have template instantiations
  using classes that themselves are templates in  the arguments (think e.g a
  vector of vectors).
  All template classes must already exist in the loaded reflection info, they
  do not work (yet) with the class loader.

  For compatibility with other bindings generators, use of square brackets
  instead of parenthesis to instantiate templates is supported as well.

* **templated functions**: Automatically participate in overloading and are
  used in the same way as other global functions.

* **templated methods**: For now, require an explicit selection of the
  template parameters.
  This will be changed to allow them to participate in overloads as expected.

* **typedefs**: Are simple python references to the actual classes to which
  they refer.

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


Templates
---------

Templates can be automatically instantiated, assuming the appropriate header
files have been loaded or are accessible to the class loader.
This is the case for example for all of STL.
For example::

    $ cat MyTemplate.h
    #include <vector>

    class MyClass {
    public:
        MyClass(int i = -99) : m_i(i) {}
        MyClass(const MyClass& s) : m_i(s.m_i) {}
        MyClass& operator=(const MyClass& s) { m_i = s.m_i; return *this; }
        ~MyClass() {}
        int m_i;
    };

Run the normal ``genreflex`` and compilation steps::

    $ genreflex MyTemplate.h --selection=MyTemplate.xml
    $ g++ -std=c++11 -fPIC -rdynamic -O2 -shared -I$CPPYYHOME/include MyTemplate_rflx.cpp -o libTemplateDict.so -L$CPPYYHOME/lib -lCling

Subsequent use should be as expected.
Note the meta-class style of "instantiating" the template::

    >>>> import cppyy
    >>>> cppyy.load_reflection_info("libTemplateDict.so")
    >>>> std = cppyy.gbl.std
    >>>> MyClass = cppyy.gbl.MyClass
    >>>> v = std.vector(MyClass)()
    >>>> v += [MyClass(1), MyClass(2), MyClass(3)]
    >>>> for m in v:
    ....     print m.m_i,
    ....
    1 2 3
    >>>>

The arguments to the template instantiation can either be a string with the
full list of arguments, or the explicit classes.
The latter makes for easier code writing if the classes passed to the
instantiation are themselves templates.


The fast lane
-------------

By default, cppyy will use direct function pointers through `CFFI`_ whenever
possible. If this causes problems for you, you can disable it by setting the
CPPYY_DISABLE_FASTPATH environment variable.

.. _CFFI: https://cffi.readthedocs.io/en/latest/


CPython
-------

Most of the ideas in cppyy come originally from the `PyROOT`_ project, which
contains a CPython-based cppyy.py module (with similar dependencies as the
one that comes with PyPy).
A standalone pip-installable version is planned, but for now you can install
ROOT through your favorite distribution installer (available in the science
section).

.. _PyROOT: https://root.cern.ch/pyroot

There are a couple of minor differences between the two versions of cppyy
(the CPython version has a few more features).
Work is on-going to integrate the nightly tests of both to make sure their
feature sets are equalized.


Python3
-------

The CPython version of cppyy supports Python3, assuming your packager has
build the backend for it.
The cppyy module has not been tested with the `Py3k`_ version of PyPy.
Note that the generated reflection information (from ``genreflex``) is fully
independent of Python, and does not need to be rebuild when switching versions
or interpreters.

.. _Py3k: https://bitbucket.org/pypy/pypy/src/py3k


.. toctree::
   :hidden:

   cppyy_example
