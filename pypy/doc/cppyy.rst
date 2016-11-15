cppyy: C++ bindings for PyPy
============================

The cppyy module creates, at run-time, Python-side classes and functions for
C++, by querying a C++ reflection system.
The default system used is `Reflex`_, which extracts the needed information
from C++ header files.
Another current backend is based on `CINT`_, and yet another, more important
one for the medium- to long-term will be based on `cling`_.
The latter sits on top of `llvm`_'s `clang`_, and will therefore allow the use
of C++11.
The work on the cling backend has so far been done only for CPython, but
bringing it to PyPy is a lot less work than developing it in the first place.

.. _Reflex: https://root.cern.ch/how/how-use-reflex
.. _CINT: https://root.cern.ch/introduction-cint
.. _cling: https://root.cern.ch/cling
.. _llvm: http://llvm.org/
.. _clang: http://clang.llvm.org/

This document describes the version of cppyy that lives in the main branch of
PyPy.
The development of cppyy happens in the "reflex-support" branch.


Motivation
----------

To provide bindings to another language in CPython, you program to a
generic C-API that exposes many of the interpreter features.
With PyPy, however, there is no such generic C-API, because several of the
interpreter features (e.g. the memory model) are pluggable and therefore
subject to change.
Furthermore, a generic API does not allow any assumptions about the calls
into another language, forcing the JIT to behave conservatively around these
calls and with the objects that cross language boundaries.
In contrast, cppyy does not expose an API, but expects one to be implemented
by a backend.
It makes strong assumptions about the semantics of the API that it uses and
that in turn allows the JIT to make equally strong assumptions.
This is possible, because the expected API is only for providing C++ language
bindings, and does not provide generic programmability.

The cppyy module further offers two features, which result in improved
performance as well as better functionality and cross-language integration.
First, cppyy itself is written in RPython and therefore open to optimizations
by the JIT up until the actual point of call into C++.
This means for example, that if variables are already unboxed by the JIT, they
can be passed through directly to C++.
Second, a backend such as Reflex (and cling far more so) adds dynamic features
to C++, thus greatly reducing impedance mismatches between the two languages.
For example, Reflex is dynamic enough to allow writing runtime bindings
generation in python (as opposed to RPython) and this is used to create very
natural "pythonizations" of the bound code.
As another example, cling allows automatic instantiations of templates.

See this description of the `cppyy architecture`_ for further details.

.. _cppyy architecture: http://morepypy.blogspot.com/2012/06/architecture-of-cppyy.html


Installation
------------

There are two ways of using cppyy, and the choice depends on how pypy-c was
built: the backend can be builtin, or dynamically loadable.
The former has the disadvantage of requiring pypy-c to be linked with external
C++ libraries (e.g. libReflex.so), but has the advantage of being faster in
some cases.
That advantage will disappear over time, however, with improvements in the
JIT.
Therefore, this document assumes that the dynamically loadable backend is
chosen (it is, by default).
See the :doc:`backend documentation <cppyy_backend>`.

A standalone version of Reflex that also provides the dynamically loadable
backend is available for `download`_. Note this is currently the only way to
get the dynamically loadable backend, so use this first.

That version, as well as any other distribution of Reflex (e.g. the one that
comes with `ROOT`_, which may be part of your Linux distribution as part of
the selection of scientific software) will also work for a build with the
builtin backend.

.. _download: http://cern.ch/wlav/reflex-2014-10-20.tar.bz2
.. _ROOT: http://root.cern.ch/

Besides Reflex, you probably need a version of `gccxml`_ installed, which is
most easily provided by the packager of your system.
If you read up on gccxml, you will probably notice that it is no longer being
developed and hence will not provide C++11 support.
That's why the medium term plan is to move to cling.
Note that gccxml is only needed to generate reflection libraries.
It is not needed to use them.

.. _gccxml: http://www.gccxml.org

To install the standalone version of Reflex, after download::

    $ tar jxf reflex-2014-10-20.tar.bz2
    $ cd reflex-2014-10-20
    $ ./build/autogen
    $ ./configure <usual set of options such as --prefix>
    $ make && make install

The usual rules apply: <prefix>/bin needs to be added to the ``PATH`` and
<prefix>/lib to the ``LD_LIBRARY_PATH`` environment variable.
For convenience, this document will assume that there is a ``REFLEXHOME``
variable that points to <prefix>.
If you downloaded or built the whole of ROOT, ``REFLEXHOME`` should be equal
to ``ROOTSYS``.

The following is optional, and is only to show how pypy-c can be build
:doc:`from source <build>`, for example to get at the main development branch of cppyy.
The :doc:`backend documentation <cppyy_backend>` has more details on the backend-specific
prerequisites.

Then run the translation to build ``pypy-c``::

    $ hg clone https://bitbucket.org/pypy/pypy
    $ cd pypy
    $ hg up reflex-support         # optional

    # This example shows python, but using pypy-c is faster and uses less memory
    $ python rpython/bin/rpython --opt=jit pypy/goal/targetpypystandalone --withmod-cppyy

This will build a ``pypy-c`` that includes the cppyy module, and through that,
Reflex support.
Of course, if you already have a pre-built version of the ``pypy`` interpreter,
you can use that for the translation rather than ``python``.
If not, you may want :ref:`to obtain a binary distribution <prebuilt-pypy>` to speed up the
translation step.


Basic bindings example
----------------------

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
    $ g++ -fPIC -rdynamic -O2 -shared -I$REFLEXHOME/include MyClass_rflx.cpp -o libMyClassDict.so -L$REFLEXHOME/lib -lReflex

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
    $ g++ -fPIC -rdynamic -O2 -shared -I$REFLEXHOME/include MyClass_rflx.cpp -o libMyClassDict.so -L$REFLEXHOME/lib -lReflex

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
    $ g++ -fPIC -rdynamic -O2 -shared -I$REFLEXHOME/include MyAdvanced_rflx.cpp -o libAdvExDict.so -L$REFLEXHOME/lib -lReflex

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
    $ g++ -fPIC -rdynamic -O2 -shared -I$REFLEXHOME/include example_rflx.cpp -o libexampleDict.so -L$REFLEXHOME/lib -lReflex

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

A bit of special care needs to be taken for the use of templates.
For a templated class to be completely available, it must be guaranteed that
said class is fully instantiated, and hence all executable C++ code is
generated and compiled in.
The easiest way to fulfill that guarantee is by explicit instantiation in the
header file that is handed to ``genreflex``.
The following example should make that clear::

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

    #ifdef __GCCXML__
    template class std::vector<MyClass>;   // explicit instantiation
    #endif

If you know for certain that all symbols will be linked in from other sources,
you can also declare the explicit template instantiation ``extern``.
An alternative is to add an object to an unnamed namespace::

    namespace {
        std::vector<MyClass> vmc;
    } // unnamed namespace

Unfortunately, this is not always enough for gcc.
The iterators of vectors, if they are going to be used, need to be
instantiated as well, as do the comparison operators on those iterators, as
these live in an internal namespace, rather than in the iterator classes.
Note that you do NOT need this iterators to iterator over a vector.
You only need them if you plan to explicitly call e.g. ``begin`` and ``end``
methods, and do comparisons of iterators.
One way to handle this, is to deal with this once in a macro, then reuse that
macro for all ``vector`` classes.
Thus, the header above needs this (again protected with
``#ifdef __GCCXML__``), instead of just the explicit instantiation of the
``vector<MyClass>``::

    #define STLTYPES_EXPLICIT_INSTANTIATION_DECL(STLTYPE, TTYPE)                      \
    template class std::STLTYPE< TTYPE >;                                             \
    template class __gnu_cxx::__normal_iterator<TTYPE*, std::STLTYPE< TTYPE > >;      \
    template class __gnu_cxx::__normal_iterator<const TTYPE*, std::STLTYPE< TTYPE > >;\
    namespace __gnu_cxx {                                                             \
    template bool operator==(const std::STLTYPE< TTYPE >::iterator&,                  \
                             const std::STLTYPE< TTYPE >::iterator&);                 \
    template bool operator!=(const std::STLTYPE< TTYPE >::iterator&,                  \
                             const std::STLTYPE< TTYPE >::iterator&);                 \
    }

    STLTYPES_EXPLICIT_INSTANTIATION_DECL(vector, MyClass)

Then, still for gcc, the selection file needs to contain the full hierarchy as
well as the global overloads for comparisons for the iterators::

    $ cat MyTemplate.xml
    <lcgdict>
        <class pattern="std::vector<*>" />
        <class pattern="std::vector<*>::iterator" />
        <function name="__gnu_cxx::operator=="/>
        <function name="__gnu_cxx::operator!="/>

        <class name="MyClass" />
    </lcgdict>

Run the normal ``genreflex`` and compilation steps::

    $ genreflex MyTemplate.h --selection=MyTemplate.xml
    $ g++ -fPIC -rdynamic -O2 -shared -I$REFLEXHOME/include MyTemplate_rflx.cpp -o libTemplateDict.so -L$REFLEXHOME/lib -lReflex

Note: this is a dirty corner that clearly could do with some automation,
even if the macro already helps.
Such automation is planned.
In fact, in the Cling world, the backend can perform the template
instantations and generate the reflection info on the fly, and none of the
above will any longer be necessary.

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

Other templates work similarly, but are typically simpler, as there are no
similar issues with iterators for e.g. ``std::list``.
The arguments to the template instantiation can either be a string with the
full list of arguments, or the explicit classes.
The latter makes for easier code writing if the classes passed to the
instantiation are themselves templates.


The fast lane
-------------

The following is an experimental feature of cppyy.
It mostly works, but there are some known issues (e.g. with return-by-value).
Soon it should be the default mode, however.

With a slight modification of Reflex, it can provide function pointers for
C++ methods, and hence allow PyPy to call those pointers directly, rather than
calling C++ through a Reflex stub.

The standalone version of Reflex `provided`_ has been patched, but if you get
Reflex from another source (most likely with a ROOT distribution), locate the
file `genreflex-methptrgetter.patch`_ in pypy/module/cppyy and apply it to
the genreflex python scripts found in ``$ROOTSYS/lib``::

    $ cd $ROOTSYS/lib
    $ patch -p2 < genreflex-methptrgetter.patch

With this patch, ``genreflex`` will have grown the ``--with-methptrgetter``
option.
Use this option when running ``genreflex``, and add the
``-Wno-pmf-conversions`` option to ``g++`` when compiling.
The rest works the same way: the fast path will be used transparently (which
also means that you can't actually find out whether it is in use, other than
by running a micro-benchmark or a JIT test).

.. _provided: http://cern.ch/wlav/reflex-2014-10-20.tar.bz2
.. _genreflex-methptrgetter.patch: https://bitbucket.org/pypy/pypy/src/default/pypy/module/cppyy/genreflex-methptrgetter.patch

CPython
-------

Most of the ideas in cppyy come originally from the `PyROOT`_ project.
Although PyROOT does not support Reflex directly, it has an alter ego called
"PyCintex" that, in a somewhat roundabout way, does.
If you installed ROOT, rather than just Reflex, PyCintex should be available
immediately if you add ``$ROOTSYS/lib`` to the ``PYTHONPATH`` environment
variable.

.. _PyROOT: https://root.cern.ch/pyroot

There are a couple of minor differences between PyCintex and cppyy, most to do
with naming.
The one that you will run into directly, is that PyCintex uses a function
called ``loadDictionary`` rather than ``load_reflection_info`` (it has the
same rootmap-based class loader functionality, though, making this point
somewhat moot).
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


Python3
-------

To change versions of CPython (to Python3, another version of Python, or later
to the `Py3k`_ version of PyPy), the only part that requires recompilation is
the bindings module, be it ``cppyy`` or ``libPyROOT.so`` (in PyCintex).
Although ``genreflex`` is indeed a Python tool, the generated reflection
information is completely independent of Python.

.. _Py3k: https://bitbucket.org/pypy/pypy/src/py3k


.. toctree::
   :hidden:

   cppyy_backend
   cppyy_example
