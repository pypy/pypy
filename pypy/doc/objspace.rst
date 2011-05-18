======================
Object Spaces
======================

.. contents::


.. _`objectspace`: 
.. _`Object Space`: 

Introduction
================

The object space creates all objects and knows how to perform operations
on the objects. You may think of an object space as being a library
offering a fixed API, a set of *operations*, with implementations that
correspond to the known semantics of Python objects.  An example of an
operation is *add*: add's implementations are, for example, responsible
for performing numeric addition when add works on numbers, concatenation
when add works on built-in sequences.

All object-space operations take and return `application-level`_ objects.
There are only a few, very simple, object-space operations which allow the
bytecode interpreter to gain some knowledge about the value of an
application-level object.
The most important one is ``is_true()``, which returns a boolean
interpreter-level value.  This is necessary to implement, for example,
if-statements (or rather, to be pedantic, to implement the
conditional-branching bytecodes into which if-statements get compiled). 

We have many working object spaces which can be plugged into
the bytecode interpreter:

- The *Standard Object Space* is a complete implementation 
  of the various built-in types and objects of Python.  The Standard Object
  Space, together with the bytecode interpreter, is the foundation of our Python
  implementation.  Internally, it is a set of `interpreter-level`_ classes
  implementing the various `application-level`_ objects -- integers, strings,
  lists, types, etc.  To draw a comparison with CPython, the Standard Object
  Space provides the equivalent of the C structures ``PyIntObject``,
  ``PyListObject``, etc.

- the *Trace Object Space* wraps e.g. the standard 
  object space in order to trace the execution of bytecodes, 
  frames and object space operations.

- various `Object Space proxies`_ wrap another object space (e.g. the standard
  one) and adds new capabilities, like lazily computed objects (computed only
  when an operation is performed on them), security-checking objects,
  distributed objects living on several machines, etc.

- the *Flow Object Space* transforms a Python program into a
  flow-graph representation, by recording all operations that the bytecode 
  interpreter would like to perform when it is shown the given Python
  program.  This technique is explained `in another document`_.

The present document gives a description of the above object spaces.
The sources of PyPy contain the various object spaces in the directory
`pypy/objspace/`_.

To choose which object space to use, use the :config:`objspace.name` option.

.. _`application-level`: coding-guide.html#application-level
.. _`interpreter-level`: coding-guide.html#interpreter-level
.. _`in another document`: translation.html

.. _interface:

Object Space Interface
======================

This is the public API that all Object Spaces implement.


Administrative Functions
----------------------------

``getexecutioncontext():``
  Return current active execution context
  (`pypy/interpreter/executioncontext.py`_).

``getbuiltinmodule(name):``
  Return a Module object for the built-in module given by name
  (`pypy/interpreter/module.py`_).

Operations on Objects in the Object Space
-----------------------------------------

These functions both take and return "wrapped" objects.

The following functions implement operations with a straightforward
semantic - they directly correspond to language-level constructs:

   ``id, type, issubtype, iter, next, repr, str, len, hash,``

   ``getattr, setattr, delattr, getitem, setitem, delitem,``

   ``pos, neg, abs, invert, add, sub, mul, truediv, floordiv, div, mod, divmod, pow, lshift, rshift, and_, or_, xor,``

   ``nonzero, hex, oct, int, float, long, ord,``

   ``lt, le, eq, ne, gt, ge, cmp, coerce, contains,``

   ``inplace_add, inplace_sub, inplace_mul, inplace_truediv, inplace_floordiv,
   inplace_div, inplace_mod, inplace_pow, inplace_lshift, inplace_rshift,
   inplace_and, inplace_or, inplace_xor,``

   ``get, set, delete, userdel``

``call(w_callable, w_args, w_kwds):``
  Call a function with the given args and keywords.

``index(w_obj):``
  Implements the index lookup (new in CPython 2.5) on 'w_obj'. Will return a
  wrapped integer or long, or raise a TypeError if the object doesn't have an
  ``__index__`` special method.

``is_(w_x, w_y):``
  Implements 'w_x is w_y'. (Returns a wrapped result too!)

``isinstance(w_obj, w_type):``
  Implements 'issubtype(type(w_obj), w_type)'. (Returns a wrapped result too!)

``exception_match(w_exc_type, w_check_class):``
  Checks if the given exception type matches 'w_check_class'. Used in matching the actual exception raised with the list of those to catch in an except clause. (Returns a wrapped result too!)

Convenience Functions
---------------------

The following functions are part of the object space interface but would not be
strictly necessary because they can be expressed using several other object
space methods. However, they are used so often that it seemed worthwhile to
introduce them as shortcuts.

``eq_w(w_obj1, w_obj2):``
  Returns true when w_obj1 and w_obj2 are equal. Shortcut for
  space.is_true(space.eq(w_obj1, w_obj2))

``is_w(w_obj1, w_obj2):``
  Shortcut for space.is_true(space.is_(w_obj1, w_obj2))

``hash_w(w_obj):``
  Shortcut for space.int_w(space.hash(w_obj))

``len_w(w_obj):``
  Shortcut for space.int_w(space.len(w_obj))

``not_(w_obj):``
  Shortcut for space.newbool(not space.is_true(w_obj))

``finditem(w_obj, w_key):``
  Equivalent to ``getitem(w_obj, w_key)`` but returns an interp-level None
  instead of raising a KeyError if the key is not found.

``call_function(w_callable, *args_w, **kw_w):``
  Convenience function that collects the arguments in a wrapped tuple and dict
  and invokes 'space.call(w_callable, ...)'.

``call_method(w_object, 'method', ...):``
   uses ``space.getattr()`` to get the method object, and then
   ``space.call_function()`` to invoke it.

``unpackiterable(w_iterable, expected_length=-1):``
  this helper iterates ``w_x``
  (using ``space.iter()`` and ``space.next()``) and collects
  the resulting wrapped objects in a list. If ``expected_length`` is given and
  the length does not match, an exception is raised.  Of course, in cases where
  iterating directly is better than collecting the elements in a list first,
  you should use ``space.iter()`` and ``space.next()`` directly.

``unpacktuple(w_tuple, expected_length=None):``
  Same as unpackiterable(), but only for tuples.

``callable(w_obj):``
  implements the built-in ``callable()``.  Returns a wrapped True or False.


Creation of Application Level objects
---------------------------------------

``wrap(x):``
  Returns a wrapped object that is a reference to the interpreter-level object
  x. This can be used either on simple immutable objects (integers,
  strings...) to create a new wrapped object, or on instances of ``Wrappable``
  to obtain an application-level-visible reference to them.  For example,
  most classes of the bytecode interpreter subclass ``Wrappable`` and can
  be directly exposed to app-level in this way - functions, frames, code
  objects, etc.

``newbool(b):``
  Creates a wrapped bool object from an interpreter level object.

``newtuple([w_x, w_y, w_z, ...]):``
  Makes a new wrapped tuple out of an interpreter level list of wrapped objects.

``newlist([..]):``
  Takes an interpreter level list of wrapped objects.

``newdict():``
  Returns a new empty dictionary.

``newslice(w_start, w_end, w_step):``
  Makes a new slice object.

``newstring(asciilist):``
  Creates a string from a list of wrapped integers.  Note that this
  is not a very useful method; usually you can just say
  space.wrap("mystring").

``newunicode(codelist):``
  Creates a unicode string from a list of integers.

Conversions from Application Level to Interpreter Level
----------------------------------------------------------

``unwrap(w_x):``
  Return the Interpreter Level equivalent of w_x.  DO NOT USE!
  Only for testing.  Use the functions described below instead.

``is_true(w_x):``
  Return a interpreter level bool (True or False) that gives the truth
  value of the wrapped object w_x.

``int_w(w_x):``
  If w_x is an application-level integer or long which can be converted without
  overflow to an integer, return an interpreter-level integer.
  Otherwise raise TypeError or OverflowError.

``bigint_w(w_x):``
  If w_x is an application-level integer or long, return an interpreter-level rbigint.
  Otherwise raise TypeError.

``str_w(w_x):``
  If w_x is an application-level string, return an interpreter-level string.
  Otherwise raise TypeError.

``float_w(w_x):``
  If w_x is an application-level float, integer or long, return interpreter-level float.
  Otherwise raise TypeError or OverflowError in case of very large longs.

``getindex_w(w_obj, w_exception=None):``
  Call `index(w_obj)`. If the resulting integer or long object can be converted
  to an interpreter-level int, return that. If not, return a clamped result if
  `w_exception` is None, otherwise raise that exception on application-level.
  (If w_obj can't be converted to an index, `index()` will raise an
  application-level TypeError.)

``interp_w(RequiredClass, w_x, can_be_None=False):``
  If w_x is a wrapped instance of the given bytecode interpreter class,
  unwrap it and return it.  If can_be_None is True, a wrapped None is also
  accepted and returns an interp-level None.  Otherwise, raises an
  OperationError encapsulating a TypeError with a nice error message.

``interpclass_w(w_x):``
  If w_x is a wrapped instance of an bytecode interpreter class -- for example
  Function, Frame, Cell, etc. -- return it unwrapped.  Otherwise return None. 


Data Members
-----------------

+ space.builtin: The Module containing the builtins
+ space.sys: The 'sys' Module
+ space.w_None: The ObjSpace's None
+ space.w_True: The ObjSpace's True
+ space.w_False: The ObjSpace's False
+ space.w_Ellipsis: The ObjSpace's Ellipsis
+ space.w_NotImplemented: The ObjSpace's NotImplemented
+ space.w_int, w_float, w_long, w_tuple, w_str, w_unicode, w_type,
  w_instance, w_slice: Python's most common type objects

+ space.w_XxxError`` for each exception class ``XxxError``
  (e.g. ``space.w_KeyError``, ``space.w_IndexError``, etc.).

+ ObjSpace.MethodTable:
   List of tuples (method name, symbol, number of arguments, list of special names) for the regular part of the interface. (Tuples are interpreter level.)

+ ObjSpace.BuiltinModuleTable:
   List of names of built-in modules.

+ ObjSpace.ConstantTable:
   List of names of the constants that the object space should define

+ ObjSpace.ExceptionTable:
   List of names of exception classes.

+ ObjSpace.IrregularOpTable:
   List of names of methods that have an irregular API (take and/or return
   non-wrapped objects).


.. _`standard object space`: 

The Standard Object Space
=========================

Introduction
------------

The Standard Object Space (`pypy/objspace/std/`_) is the direct equivalent of CPython's
object library (the "Objects/" subdirectory in the distribution). It is an
implementation of the common Python types in a lower-level language.

The Standard Object Space defines an abstract parent class, W_Object, and a
bunch of subclasses like W_IntObject, W_ListObject, and so on. A wrapped
object (a "black box" for the bytecode interpreter main loop) is thus an
instance of one of these classes. When the main loop invokes an operation, say
the addition, between two wrapped objects w1 and w2, the Standard Object Space
does some internal dispatching (similar to "Object/abstract.c" in CPython) and
invokes a method of the proper W_XyzObject class that can do the
operation. The operation itself is done with the primitives allowed by
RPython. The result is constructed as a wrapped object again. For
example, compare the following implementation of integer addition with the
function "int_add()" in "Object/intobject.c": :: 

    def add__Int_Int(space, w_int1, w_int2):
        x = w_int1.intval
        y = w_int2.intval
        try:
            z = ovfcheck(x + y)
        except OverflowError:
            raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer addition"))
        return W_IntObject(space, z)

Why such a burden just for integer objects? Why did we have to wrap them into
W_IntObject instances? For them it seems it would have been sufficient just to
use plain Python integers. But this argumentation fails just like it fails for
more complex kind of objects. Wrapping them just like everything else is the
cleanest solution. You could introduce case testing wherever you use a wrapped
object, to know if it is a plain integer or an instance of (a subclass of)
W_Object. But that makes the whole program more complicated. The equivalent in
CPython would be to use PyObject* pointers all around except when the object is
an integer (after all, integers are directly available in C too). You could
represent small integers as odd-valuated pointers. But it puts extra burden on
the whole C code, so the CPython team avoided it.  (In our case it is an
optimization that we eventually made, but not hard-coded at this level -
see `Standard Interpreter Optimizations`_.)

So in summary: wrapping integers as instances is the simple path, while
using plain integers instead is the complex path, not the other way
around.


Object types
------------

The larger part of the `pypy/objspace/std/`_ package defines and implements the
library of Python's standard built-in object types.  Each type (int, float,
list, tuple, str, type, etc.) is typically implemented by two modules:

* the *type specification* module, which for a type ``xxx`` is called ``xxxtype.py``;

* the *implementation* module, called ``xxxobject.py``.

The ``xxxtype.py`` module basically defines the type object itself.  For
example, `pypy/objspace/std/listtype.py`_ contains the specification of the object you get when
you type ``list`` in a PyPy prompt.  `pypy/objspace/std/listtype.py`_ enumerates the methods
specific to lists, like ``append()``.

A particular method implemented by all types is the ``__new__()`` special
method, which in Python's new-style-classes world is responsible for creating
an instance of the type.  In PyPy, ``__new__()`` locates and imports the module
implementing *instances* of the type, and creates such an instance based on the
arguments the user supplied to the constructor.  For example, `pypy/objspace/std/tupletype.py`_
defines ``__new__()`` to import the class ``W_TupleObject`` from
`pypy/objspace/std/tupleobject.py`_ and instantiate it.  The `pypy/objspace/std/tupleobject.py`_ then contains a
"real" implementation of tuples: the way the data is stored in the
``W_TupleObject`` class, how the operations work, etc.

The goal of the above module layout is to cleanly separate the Python
type object, visible to the user, and the actual implementation of its
instances.  It is possible to provide *several* implementations of the
instances of the same Python type, by writing several ``W_XxxObject``
classes.  Every place that instantiates a new object of that Python type
can decide which ``W_XxxObject`` class to instantiate.  For example, the
regular string implementation is ``W_StringObject``, but we also have a
``W_StringSliceObject`` class whose instances contain a string, a start
index, and a stop index; it is used as the result of a string slicing
operation to avoid the copy of all the characters in the slice into a
new buffer.

From the user's point of view, the multiple internal ``W_XxxObject``
classes are not visible: they are still all instances of exactly the
same Python type.  PyPy knows that (e.g.) the application-level type of
its interpreter-level ``W_StringObject`` instances is str because
there is a ``typedef`` class attribute in ``W_StringObject`` which
points back to the string type specification from `pypy/objspace/std/stringtype.py`_; all
other implementations of strings use the same ``typedef`` from
`pypy/objspace/std/stringtype.py`_.

For other examples of multiple implementations of the same Python type,
see `Standard Interpreter Optimizations`_.

.. _`Standard Interpreter Optimizations`: interpreter-optimizations.html


Multimethods
------------

The Standard Object Space allows multiple object implementations per
Python type - this is based on multimethods_.  For a description of the
multimethod variant that we implemented and which features it supports,
see the comment at the start of `pypy/objspace/std/multimethod.py`_.  However, multimethods
alone are not enough for the Standard Object Space: the complete picture
spans several levels in order to emulate the exact Python semantics.

Consider the example of the ``space.getitem(w_a, w_b)`` operation,
corresponding to the application-level syntax ``a[b]``.  The Standard
Object Space contains a corresponding ``getitem`` multimethod and a
family of functions that implement the multimethod for various
combination of argument classes - more precisely, for various
combinations of the *interpreter-level* classes of the arguments.  Here
are some examples of functions implementing the ``getitem``
multimethod:

* ``getitem__Tuple_ANY``: called when the first argument is a
  W_TupleObject, this function converts its second argument to an
  integer and performs tuple indexing.

* ``getitem__Tuple_Slice``: called when the first argument is a
  W_TupleObject and the second argument is a W_SliceObject.  This
  version takes precedence over the previous one if the indexing is
  done with a slice object, and performs tuple slicing instead.

* ``getitem__String_Slice``: called when the first argument is a
  W_StringObject and the second argument is a slice object.  When the
  special string slices optimization is enabled, this returns an
  instance of W_StringSliceObject.

* ``getitem__StringSlice_ANY``: called when the first argument is a
  W_StringSliceObject.  This implementation adds the provided index to
  the original start of the slice stored in the W_StringSliceObject
  instance.  This allows constructs like ``a = s[10:100]; print a[5]``
  to return the 15th character of ``s`` without having to perform any
  buffer copying.

Note how the multimethod dispatch logic helps writing new object
implementations without having to insert hooks into existing code.  Note
first how we could have defined a regular method-based API that new
object implementations must provide, and call these methods from the
space operations.  The problem with this approach is that some Python
operators are naturally binary or N-ary.  Consider for example the
addition operation: for the basic string implementation it is a simple
concatenation-by-copy, but it can have a rather more subtle
implementation for strings done as ropes.  It is also likely that
concatenating a basic string with a rope string could have its own
dedicated implementation - and yet another implementation for a rope
string with a basic string.  With multimethods, we can have an
orthogonally-defined implementation for each combination.

The multimethods mechanism also supports delegate functions, which are
converters between two object implementations.  The dispatch logic knows
how to insert calls to delegates if it encounters combinations of
interp-level classes which is not directly implemented.  For example, we
have no specific implementation for the concatenation of a basic string
and a StringSlice object; when the user adds two such strings, then the
StringSlice object is converted to a basic string (that is, a
temporarily copy is built), and the concatenation is performed on the
resulting pair of basic strings.  This is similar to the C++ method
overloading resolution mechanism (but occurs at runtime).

.. _multimethods: http://en.wikipedia.org/wiki/Multimethods


Multimethod slicing
-------------------

The complete picture is more complicated because the Python object model
is based on *descriptors*: the types ``int``, ``str``, etc. must have
methods ``__add__``, ``__mul__``, etc. that take two arguments including
the ``self``.  These methods must perform the operation or return
``NotImplemented`` if the second argument is not of a type that it
doesn't know how to handle.

The Standard Object Space creates these methods by *slicing* the
multimethod tables.  Each method is automatically generated from a
subset of the registered implementations of the corresponding
multimethod.  This slicing is performed on the first argument, in order
to keep only the implementations whose first argument's
interpreter-level class matches the declared Python-level type.

For example, in a baseline PyPy, ``int.__add__`` is just calling the
function ``add__Int_Int``, which is the only registered implementation
for ``add`` whose first argument is an implementation of the ``int``
Python type.  On the other hand, if we enable integers implemented as
tagged pointers, then there is another matching implementation:
``add__SmallInt_SmallInt``.  In this case, the Python-level method
``int.__add__`` is implemented by trying to dispatch between these two
functions based on the interp-level type of the two arguments.

Similarly, the reverse methods (``__radd__`` and others) are obtained by
slicing the multimethod tables to keep only the functions whose *second*
argument has the correct Python-level type.

Slicing is actually a good way to reproduce the details of the object
model as seen in CPython: slicing is attempted for every Python types
for every multimethod, but the ``__xyz__`` Python methods are only put
into the Python type when the resulting slices are not empty.  This is
how our ``int`` type has no ``__getitem__`` method, for example.
Additionally, slicing ensures that ``5 .__add__(6L)`` correctly returns
``NotImplemented`` (because this particular slice does not include
``add__Long_Long`` and there is no ``add__Int_Long``), which leads to
``6L.__radd__(5)`` being called, as in CPython.


The Trace Object Space
======================

The Trace Object Space was first written at the Amsterdam sprint.  The ease
with which the Trace Object Space was implemented in `pypy/objspace/trace.py`_
underlines the power of the Object Space abstraction.  Effectively it is a
simple proxy object space.  It has gone through various refactors to reach its
original objective, which was to show how bytecode in code objects ultimately
performs computation via an object space.

This space will intercept space operations in realtime and as a side effect
will memorize them.  It also traces frame creation, deletion and bytecode
execution.  Its implementation delegates to another object space - usually the
standard object space - in order to carry out the operations.

The pretty printing aims to be a graphical way of introducing programmers, and
especially ones familiar with CPython, to how PyPy works from a bytecode and
frames perspective.  As a result one can grasp an intuitive idea of how
`Abstract Interpretation`_ records via tracing all execution paths of the
individual operations if one removes the bytecode out of the equation.  This is
the purpose of the `Flow Object Space`_.

Another educational use of Trace Object Space is that it allows a Python user
who has little understanding of how the interpreter works, a rapid way of
understanding what bytecodes are and what an object space is.  When a statement
or expression is typed on the command line, one can see what is happening
behind the scenes.  This will hopefully give users a better mental framework
when they are writing code.

To make use of the tracing facilities you can at runtime switch
your interactive session to tracing mode by typing:: 

    >>> __pytrace__ = 1 

Note that tracing mode will not show or record all space operations 
by default to avoid presenting too much information.  Only non-helper 
operations are usually shown.   

A quick introduction on how to use the trace object space can be `found here`_.
A number of options for configuration is here in `pypy/tool/traceconfig.py`_.


.. _`found here` : getting-started-dev.html#tracing-bytecode-and-operations-on-objects
.. _`Abstract Interpretation`: http://en.wikipedia.org/wiki/Abstract_interpretation

.. _`Flow Object Space`:

The Flow Object Space
=====================

Introduction
------------

The task of the FlowObjSpace (the source is at `pypy/objspace/flow/`_) is to generate a control-flow graph from a
function.  This graph will also contain a trace of the individual operations, so
that it is actually just an alternate representation for the function.

The FlowObjSpace is an object space, which means that it exports the standard
object space interface and it is driven by the bytecode interpreter.

The basic idea is that if the bytecode interpreter is given a function, e.g.::

  def f(n):
    return 3*n+2

it will do whatever bytecode dispatching and stack-shuffling needed, during
which it issues a sequence of calls to the object space.  The FlowObjSpace
merely records these calls (corresponding to "operations") in a structure called
a basic block.  To track which value goes where, the FlowObjSpace invents
placeholder "wrapped objects" and give them to the interpreter, so that they
appear in some next operation.  This technique is an example of `Abstract
Interpretation`_.

.. _`Abstract Interpretation`: http://en.wikipedia.org/wiki/Abstract_interpretation

For example, if the placeholder ``v1`` is given as the argument to the above
function, the bytecode interpreter will call ``v2 = space.mul(space.wrap(3),
v1)`` and then ``v3 = space.add(v2, space.wrap(2))`` and return ``v3`` as the
result.  During these calls the FlowObjSpace will record a basic block:: 

  Block(v1):     # input argument
    v2 = mul(Constant(3), v1)
    v3 = add(v2, Constant(2))



The Flow model
--------------

The data structures built up by the flow object space are described in the
`translation document`_.

.. _`translation document`: translation.html#flow-model


How the FlowObjSpace works
--------------------------

The FlowObjSpace works by recording all operations issued by the bytecode
interpreter into basic blocks.  A basic block ends in one of two cases: when
the bytecode interpreters calls ``is_true()``, or when a joinpoint is reached.

* A joinpoint occurs when the next operation is about to be recorded into the
  current block, but there is already another block that records an operation
  for the same bytecode position.  This means that the bytecode interpreter
  has closed a loop and is interpreting already-seen code again.  In this
  situation, we interrupt the bytecode interpreter and we make a link from the
  end of the current block back to the previous block, thus closing the loop
  in the flow graph as well.  (Note that this occurs only when an operation is
  about to be recorded, which allows some amount of constant-folding.) 

* If the bytecode interpreter calls ``is_true()``, the FlowObjSpace doesn't
  generally know if the answer should be True or False, so it puts a
  conditional jump and generates two successor blocks for the current basic
  block.  There is some trickery involved so that the bytecode interpreter is
  fooled into thinking that ``is_true()`` first returns False (and the
  subsequent operations are recorded in the first successor block), and later
  the *same* call to ``is_true()`` also returns True (and the subsequent
  operations go this time to the other successor block). 

(This section to be extended...)


Object Space proxies
====================

We have implemented several *proxy object spaces* which wrap another
space (typically the standard one) and add some capability to all
objects.  These object spaces are documented in a separate page: `What
PyPy can do for your objects`_.

.. _`What PyPy can do for your objects`: objspace-proxies.html

.. include:: _ref.txt
