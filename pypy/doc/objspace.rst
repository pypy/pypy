The Object Space
================

.. contents::


.. _objectspace:
.. _Object Space:

Introduction
------------

The object space creates all objects in PyPy, and knows how to perform operations
on them. It may be helpful to think of an object space as being a library
offering a fixed API: a set of *operations*, along with implementations that
correspond to the known semantics of Python objects.

For example, :py:func:`add` is an operation, with implementations in the object
space that perform numeric addition (when :py:func:`add` is operating on numbers),
concatenation (when :py:func:`add` is operating on sequences), and so on.

We have some working object spaces which can be plugged into
the bytecode interpreter:

- The *Standard Object Space* is a complete implementation
  of the various built-in types and objects of Python.  The Standard Object
  Space, together with the bytecode interpreter, is the foundation of our Python
  implementation.  Internally, it is a set of :ref:`interpreter-level <interpreter-level>` classes
  implementing the various :ref:`application-level <application-level>` objects -- integers, strings,
  lists, types, etc.  To draw a comparison with CPython, the Standard Object
  Space provides the equivalent of the C structures :c:type:`PyIntObject`,
  :c:type:`PyListObject`, etc.

- various `Object Space proxies`_ wrap another object space (e.g. the standard
  one) and adds new capabilities, like lazily computed objects (computed only
  when an operation is performed on them), security-checking objects,
  distributed objects living on several machines, etc.

The present document gives a description of the above object spaces.
The sources of PyPy contain the various object spaces in the directory
:source:`pypy/objspace/`.

.. TODO: what to do with these paragraphs?

All object-space operations take and return :ref:`application-level <application-level>` objects.
There are only a few, very simple, object-space operations which allow the
bytecode interpreter to gain some knowledge about the value of an
application-level object.

The most important one is :py:func:`is_true`, which returns a boolean
interpreter-level value.  This is necessary to implement, for example,
if-statements (or rather, to be pedantic, to implement the
conditional-branching bytecodes into which if-statements get compiled).

.. TODO: audit ^^

.. _objspace-interface:

Object Space Interface
----------------------

This is the public API that all Object Spaces implement:


Administrative Functions
~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: getexecutioncontext()

  Return the currently active execution context.
  (:source:`pypy/interpreter/executioncontext.py`).

.. py:function:: getbuiltinmodule(name)

  Return a :py:class:`Module` object for the built-in module given by ``name``.
  (:source:`pypy/interpreter/module.py`).


Operations on Objects in the Object Space
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These functions both take and return "wrapped" (i.e. :ref:`application-level <application-level>`) objects.

The following functions implement operations with straightforward semantics -
they directly correspond to language-level constructs:

   ``id, type, issubtype, iter, next, repr, str, len, hash,``

   ``getattr, setattr, delattr, getitem, setitem, delitem,``

   ``pos, neg, abs, invert, add, sub, mul, truediv, floordiv, div, mod, divmod, pow, lshift, rshift, and_, or_, xor,``

   ``nonzero, hex, oct, int, float, long, ord,``

   ``lt, le, eq, ne, gt, ge, cmp, coerce, contains,``

   ``inplace_add, inplace_sub, inplace_mul, inplace_truediv, inplace_floordiv,
   inplace_div, inplace_mod, inplace_pow, inplace_lshift, inplace_rshift,
   inplace_and, inplace_or, inplace_xor,``

   ``get, set, delete, userdel``

.. py:function:: call(w_callable, w_args, w_kwds)

  Calls a function with the given positional (``w_args``) and keyword (``w_kwds``)
  arguments.

.. py:function:: index(w_obj)

  Implements index lookup (`as introduced in CPython 2.5`_) using ``w_obj``. Will return a
  wrapped integer or long, or raise a :py:exc:`TypeError` if the object doesn't have an
  :py:func:`__index__` special method.

.. _as introduced in CPython 2.5: http://www.python.org/dev/peps/pep-0357/

.. py:function:: is_(w_x, w_y)

  Implements ``w_x is w_y``.

.. py:function:: isinstance(w_obj, w_type)

  Implements :py:func:`issubtype` with ``type(w_obj)`` and ``w_type`` as arguments.

.. py:function::exception_match(w_exc_type, w_check_class)

  Checks if the given exception type matches :py:obj:`w_check_class`. Used in
  matching the actual exception raised with the list of those to catch in an
  except clause.


Convenience Functions
~~~~~~~~~~~~~~~~~~~~~

The following functions are used so often that it seemed worthwhile to introduce
them as shortcuts -- however, they are not strictly necessary since they can be
expressed using several other object space methods.

.. py:function:: eq_w(w_obj1, w_obj2)

  Returns :py:const:`True` when :py:obj:`w_obj1` and :py:obj:`w_obj2` are equal.
  Shortcut for ``space.is_true(space.eq(w_obj1, w_obj2))``.

.. py:function:: is_w(w_obj1, w_obj2)

  Shortcut for ``space.is_true(space.is_(w_obj1, w_obj2))``.

.. py:function:: hash_w(w_obj)

  Shortcut for ``space.int_w(space.hash(w_obj))``.

.. py:function:: len_w(w_obj)

  Shortcut for ``space.int_w(space.len(w_obj))``.

*NOTE* that the above four functions return :ref:`interpreter-level <interpreter-level>`
objects, not :ref:`application-level <application-level>` ones!

.. py:function:: not_(w_obj)

  Shortcut for ``space.newbool(not space.is_true(w_obj))``.

.. py:function:: finditem(w_obj, w_key)

  Equivalent to ``getitem(w_obj, w_key)`` but returns an **interpreter-level** None
  instead of raising a KeyError if the key is not found.

.. py:function:: call_function(w_callable, *args_w, **kw_w)

  Collects the arguments in a wrapped tuple and dict and invokes
  ``space.call(w_callable, ...)``.

.. py:function:: call_method(w_object, 'method', ...)

  Uses :py:meth:`space.getattr` to get the method object, and then :py:meth:`space.call_function` to invoke it.

.. py:function:: unpackiterable(w_iterable[, expected_length=-1])

  Iterates over :py:obj:`w_x` (using :py:meth:`space.iter` and :py:meth:`space.next()`)
  and collects the resulting wrapped objects in a list. If ``expected_length`` is
  given and the length does not match, raises an exception.

  Of course, in cases where iterating directly is better than collecting the
  elements in a list first, you should use :py:meth:`space.iter` and :py:meth:`space.next`
  directly.

.. py:function:: unpacktuple(w_tuple[, expected_length=None])

  Equivalent to :py:func:`unpackiterable`, but only for tuples.

.. py:function:: callable(w_obj)

  Implements the built-in :py:func:`callable`.


Creation of Application Level objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: wrap(x)

  Returns a wrapped object that is a reference to the interpreter-level object
  :py:obj:`x`. This can be used either on simple immutable objects (integers,
  strings, etc) to create a new wrapped object, or on instances of :py:class:`W_Root`
  to obtain an application-level-visible reference to them.  For example,
  most classes of the bytecode interpreter subclass :py:class:`W_Root` and can
  be directly exposed to app-level in this way - functions, frames, code
  objects, etc.

.. py:function:: newbool(b)

  Creates a wrapped :py:class:`bool` object from an :ref:`interpreter-level <interpreter-level>` object.

.. py:function:: newtuple([w_x, w_y, w_z, ...])

  Creates a new wrapped tuple out of an interpreter-level list of wrapped objects.

.. py:function:: newlist([..])

  Creates a wrapped :py:class:`list` from an interpreter-level list of wrapped objects.

.. py:function:: newdict

  Returns a new empty dictionary.

.. py:function:: newslice(w_start, w_end, w_step)

  Creates a new slice object.

.. py:function:: newstring(asciilist)

  Creates a string from a list of wrapped integers. Note that this may not be
  a very useful method; usually you can just say ``space.wrap("mystring")``.

.. py:function:: newunicode(codelist)

  Creates a Unicode string from a list of integers (code points).


Conversions from Application Level to Interpreter Level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: unwrap(w_x)

  Returns the interpreter-level equivalent of :py:obj:`w_x` -- use this **ONLY** for
  testing! In most circumstances you should use the functions described below instead.

.. py:function:: is_true(w_x)

  Returns a interpreter-level boolean (:py:const:`True` or :py:const:`False`) that
  gives the truth value of the wrapped object :py:obj:`w_x`.

.. py:function:: int_w(w_x)

  If :py:obj:`w_x` is an application-level integer or long which can be converted
  without overflow to an integer, return an interpreter-level integer. Otherwise
  raise :py:exc:`TypeError` or :py:exc:`OverflowError`.

.. py:function:: bigint_w(w_x)

  If :py:obj:`w_x` is an application-level integer or long, return an interpreter-level
  :py:class:`rbigint`. Otherwise raise :py:exc:`TypeError`.

.. py:function:: str_w(w_x)

  If :py:obj:`w_x` is an application-level string, return an interpreter-level string.
  Otherwise raise :py:exc:`TypeError`.

.. py:function:: float_w(w_x)

  If :py:obj:`w_x` is an application-level float, integer or long, return interpreter-level
  float. Otherwise raise :py:exc:`TypeError` (or :py:exc:`OverflowError` in case
  of very large longs).

.. py:function:: getindex_w(w_obj[, w_exception=None])

  Call ``index(w_obj)``. If the resulting integer or long object can be converted
  to an interpreter-level :py:class:`int`, return that. If not, return a clamped
  result if :py:obj:`w_exception` is None, otherwise raise that exception at the
  application level.

  (If :py:obj:`w_obj` can't be converted to an index, :py:func:`index` will raise an
  application-level :py:exc:`TypeError`.)

.. py:function:: interp_w(RequiredClass, w_x[, can_be_None=False])

  If :py:obj:`w_x` is a wrapped instance of the given bytecode interpreter class,
  unwrap it and return it.  If :py:obj:`can_be_None` is :py:const:`True`, a wrapped
  :py:const:`None` is also accepted and returns an interpreter-level :py:const:`None`.
  Otherwise, raises an :py:exc:`OperationError` encapsulating a :py:exc:`TypeError`
  with a nice error message.

.. py:function:: interpclass_w(w_x)

  If :py:obj:`w_x` is a wrapped instance of an bytecode interpreter class -- for
  example :py:class:`Function`, :py:class:`Frame`, :py:class:`Cell`, etc. -- return
  it unwrapped.  Otherwise return :py:const:`None`.


Data Members
~~~~~~~~~~~~

.. py:data:: space.builtin

  The :py:class:`Module` containing the builtins.

.. py:data:: space.sys

 The ``sys`` :py:class:`Module`.

.. py:data:: space.w_None

  The ObjSpace's instance of :py:const:`None`.

.. py:data:: space.w_True

  The ObjSpace's instance of :py:const:`True`.

.. py:data:: space.w_False

  The ObjSpace's instance of :py:const:`False`.

.. py:data:: space.w_Ellipsis

  The ObjSpace's instance of :py:const:`Ellipsis`.

.. py:data:: space.w_NotImplemented

  The ObjSpace's instance of :py:const:`NotImplemented`.

.. py:data:: space.w_int
             space.w_float
             space.w_long
             space.w_tuple
             space.w_str
             space.w_unicode
             space.w_type
             space.w_instance
             space.w_slice

  Python's most common type objects.

.. py:data:: space.w_[XYZ]Error

  Python's built-in exception classes (:py:class:`KeyError`, :py:class:`IndexError`,
  etc)

.. py:data:: ObjSpace.MethodTable

  List of tuples containing ``(method_name, symbol, number_of_arguments, list_of_special_names)``
  for the regular part of the interface. **NOTE** that tuples are interpreter-level.

.. py:data:: ObjSpace.BuiltinModuleTable

  List of names of built-in modules.

.. py:data:: ObjSpace.ConstantTable

  List of names of the constants that the object space should define.

.. py:data:: ObjSpace.ExceptionTable

  List of names of exception classes.

.. py:data:: ObjSpace.IrregularOpTable

  List of names of methods that have an irregular API (take and/or return
  non-wrapped objects).


.. _standard-object-space:

The Standard Object Space
-------------------------

Introduction
~~~~~~~~~~~~

The Standard Object Space (:source:`pypy/objspace/std/`) is the direct equivalent
 of CPython's object library (the ``Objects/`` subdirectory in the distribution).
It is an implementation of the common Python types in a lower-level language.

The Standard Object Space defines an abstract parent class, :py:class:`W_Object`
as well as subclasses like :py:class:`W_IntObject`, :py:class:`W_ListObject`,
and so on. A wrapped object (a "black box" for the bytecode interpreter's main
loop) is an instance of one of these classes. When the main loop invokes an
operation (for example: addition), between two wrapped objects :py:obj:`w1` and
:py:obj:`w2`, the Standard Object Space does some internal dispatching (similar
to ``Object/abstract.c`` in CPython) and invokes a method of the proper
:py:class:`W_XYZObject` class that can perform the operation.

The operation itself is done with the primitives allowed by RPython, and the
result is constructed as a wrapped object. For example, compare the following
implementation of integer addition with the function :c:func:`int_add()` in
``Object/intobject.c``: ::

    def add__Int_Int(space, w_int1, w_int2):
        x = w_int1.intval
        y = w_int2.intval
        try:
            z = ovfcheck(x + y)
        except OverflowError:
            raise FailedToImplementArgs(space.w_OverflowError,
                                    space.wrap("integer addition"))
        return W_IntObject(space, z)

.. TODO: Rewrite the below

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
see :doc:`interpreter-optimizations`.)

So in summary: wrapping integers as instances is the simple path, while
using plain integers instead is the complex path, not the other way
around.


Object types
~~~~~~~~~~~~

The largest part of the :source:`pypy/objspace/std` package defines and implements
the library of Python's built-in object types.  Each type (:py:class:`int`,
:py:class:`float`, :py:class:`list`, :py:class:`tuple`, :py:class:`str`, :py:class:`type`,
etc.) is typically implemented by two modules:

* the *type specification* module, which for a type ``xyz`` is called ``xyztype.py``;

* the *implementation* module, called ``xyzobject.py``.

The ``xyztype.py`` module defines the type object itself.  For example,
:source:`pypy/objspace/std/listtype.py` contains the specification of the object
you get when you type :py:class:`list` in a PyPy prompt, and enumerates the
methods specific to lists, like :py:meth:`append`.

A particular method implemented by all types is the :py:meth:`__new__` special
method, which in Python's new-style-classes world is responsible for creating
an instance of the type. In PyPy, :py:meth:`__new__` locates and imports the
module implementing *instances* of the type, and creates such an instance based
on the arguments the user supplied to the constructor.  For example, :source:`pypy/objspace/std/tupletype.py`
defines :py:meth:`__new__` to import the class :py:class:`W_TupleObject` from
:source:`pypy/objspace/std/tupleobject.py` and instantiate it.  The :source:`pypy/objspace/std/tupleobject.py` contains a
"real" implementation of tuples: the way the data is stored in the :py:class:`W_TupleObject`
class, how the operations work, etc.

The goal of the above module layout is to cleanly separate the Python
type object, visible to the user, and the actual implementation of its
instances.  It is possible to provide *several* implementations of the
instances of the same Python type, by writing several :py:class:`W_XyzObject`
classes.  Every place that instantiates a new object of that Python type
can decide which :py:class:`W_XyzObject` class to instantiate.

From the user's point of view, the multiple internal :py:class:`W_XyzObject`
classes are not visible: they are still all instances of exactly the
same Python type.  PyPy knows that (e.g.) the application-level type of
its interpreter-level :py:class:`W_StringObject` instances is :py:class:`str`
because there is a ``typedef`` class attribute in :py:class:`W_StringObject`
which points back to the string type specification from :source:`pypy/objspace/std/stringtype.py`;
all other implementations of strings use the same ``typedef`` from
:source:`pypy/objspace/std/stringtype.py`.

For other examples of multiple implementations of the same Python type,
see :doc:`interpreter-optimizations`.


Multimethods
~~~~~~~~~~~~

The Standard Object Space allows multiple object implementations per
Python type - this is based on multimethods_.  For a description of the
multimethod variant that we implemented and which features it supports,
see the comments at the start of :source:`pypy/objspace/std/multimethod.py`.
However, multimethods alone are not enough for the Standard Object Space: the
complete picture spans several levels in order to emulate the exact Python
semantics.

Consider the example of the ``space.getitem(w_a, w_b)`` operation,
corresponding to the application-level syntax ``a[b]``.  The Standard
Object Space contains a corresponding ``getitem`` multimethod and a
family of functions that implement the multimethod for various
combination of argument classes - more precisely, for various
combinations of the :ref:`interpreter-level <interpreter-level>` classes of
the arguments.  Here are some examples of functions implementing the ``getitem``
multimethod:

.. py:function:: getitem__Tuple_ANY

  Called when the first argument is a :py:class:`W_TupleObject`, this function
  converts its second argument to an integer and performs tuple indexing.

.. py:function:: getitem__Tuple_Slice

  Called when the first argument is a :py:class:`W_TupleObject` and the second
  argument is a :py:class:`W_SliceObject`.  This version takes precedence over
  the previous one if the indexing is done with a slice object, and performs
  tuple slicing instead.

.. py:function:: getitem__String_Slice

  Called when the first argument is a :py:class:`W_StringObject` and the second
  argument is a slice object.

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
interpreter-level classes which is not directly implemented.  For example, we
have no specific implementation for the concatenation of a basic string
and a StringSlice object; when the user adds two such strings, then the
StringSlice object is converted to a basic string (that is, a
temporary copy is built), and the concatenation is performed on the
resulting pair of basic strings.  This is similar to the C++ method
overloading resolution mechanism (but occurs at runtime).

.. _multimethods: http://en.wikipedia.org/wiki/Multimethods


Multimethod slicing
~~~~~~~~~~~~~~~~~~~

The complete picture is more complicated because the Python object model
is based on descriptors_: the types :py:class:`int`, :py:class:`str`, etc. must
have methods :py:meth:`__add__`, :py:meth:`__mul__`, etc. that take two
arguments including the :py:obj:`self`.  These methods must perform the
operation or return :py:exc:`NotImplemented` if the second argument is not of
a type that it knows how to handle.

.. _descriptors: http://docs.python.org/2/howto/descriptor.html

The Standard Object Space creates these methods by *slicing* the
multimethod tables.  Each method is automatically generated from a
subset of the registered implementations of the corresponding
multimethod.  This slicing is performed on the first argument, in order
to keep only the implementations whose first argument's
interpreter-level class matches the declared Python-level type.

For example, in a baseline PyPy, :py:meth:`int.__add__` just calls the
function :py:func:`add__Int_Int`, which is the only registered implementation
for :py:func:`add` whose first argument is an implementation of the :py:class:`int`
Python type.  On the other hand, if we enable integers implemented as
tagged pointers, then there is another matching implementation:
:py:func:`add__SmallInt_SmallInt`.  In this case, the Python-level method
:py:meth:`int.__add__` is implemented by trying to dispatch between these two
functions based on the interpreter-level type of the two arguments.

Similarly, the reverse methods (:py:meth:`__radd__` and others) are obtained by
slicing the multimethod tables to keep only the functions whose *second*
argument has the correct Python-level type.

Slicing is actually a good way to reproduce the details of the object
model as seen in CPython: slicing is attempted for every Python type
for every multimethod, but the :py:meth:`__xyz__` Python methods are only put
into the Python type when the resulting slices are not empty.  This is
how our :py:class:`int` type has no :py:meth:`__getitem__` method, for example.
Additionally, slicing ensures that ``5 .__add__(6L)`` correctly returns
:py:exc:`NotImplemented` (because this particular slice does not include
:py:func:`add__Long_Long` and there is no :py:func:`add__Int_Long`), which leads to
``6L.__radd__(5)`` being called, as in CPython.


Object Space proxies
--------------------

We have implemented several *proxy object spaces* which wrap another
space (typically the standard one) and add some capability to all
objects.  These object spaces are documented in a separate page:
:doc:`objspace-proxies`
