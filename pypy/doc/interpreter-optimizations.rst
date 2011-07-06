==================================
Standard Interpreter Optimizations
==================================

.. contents:: Contents

Introduction
============

One of the advantages -- indeed, one of the motivating goals -- of the PyPy
standard interpreter (compared to CPython) is that of increased flexibility and
configurability.

One example of this is that we can provide several implementations of the same
object (e.g. lists) without exposing any difference to application-level
code. This makes it easy to provide a specialized implementation of a type that
is optimized for a certain situation without disturbing the implementation for
the regular case.

This document describes several such optimizations.  Most of them are not
enabled by default.  Also, for many of these optimizations it is not clear
whether they are worth it in practice for a real-world application (they sure
make some microbenchmarks a lot faster and use less memory, which is not saying
too much).  If you have any observation in that direction, please let us know!
By the way: alternative object implementations are a great way to get into PyPy
development since you have to know only a rather small part of PyPy to do
them. And they are fun too!

.. describe other optimizations!

Object Optimizations
====================

String Optimizations
--------------------

String-Join Objects
+++++++++++++++++++

String-join objects are a different implementation of the Python ``str`` type,
They represent the lazy addition of several strings without actually performing
the addition (which involves copying etc.). When the actual value of the string
join object is needed, the addition is performed. This makes it possible to
perform repeated string additions in a loop without using the
``"".join(list_of_strings)`` pattern.

You can enable this feature enable with the :config:`objspace.std.withstrjoin`
option.

String-Slice Objects
++++++++++++++++++++

String-slice objects are another implementation of the Python ``str`` type.
They represent the lazy slicing of a string without actually performing the
slicing (which would involve copying). This is only done for slices of step
one. When the actual value of the string slice object is needed, the slicing
is done (although a lot of string methods don't make this necessary). This
makes string slicing a very efficient operation. It also saves memory in some
cases but can also lead to memory leaks, since the string slice retains a
reference to the original string (to make this a bit less likely, we don't
use lazy slicing when the slice would be much shorter than the original
string.  There is also a minimum number of characters below which being lazy
is not saving any time over making the copy).

You can enable this feature with the :config:`objspace.std.withstrslice` option.

Ropes
+++++

Ropes are a general flexible string implementation, following the paper `"Ropes:
An alternative to Strings."`_ by Boehm, Atkinson and Plass. Strings are
represented as balanced concatenation trees, which makes slicing and
concatenation of huge strings efficient.

Using ropes is usually not a huge benefit for normal Python programs that use
the typical pattern of appending substrings to a list and doing a
``"".join(l)`` at the end. If ropes are used, there is no need to do that.
A somewhat silly example of things you can do with them is this::

    $ bin/py.py --objspace-std-withrope
    faking <type 'module'>
    PyPy 1.5.0-alpha0 in StdObjSpace on top of Python 2.7.1+ (startuptime: 11.38 secs)
    >>>> import sys
    >>>> sys.maxint
    2147483647
    >>>> s = "a" * sys.maxint
    >>>> s[10:20]
    'aaaaaaaaaa'


You can enable this feature with the :config:`objspace.std.withrope` option.

.. _`"Ropes: An alternative to Strings."`: http://citeseer.ist.psu.edu/viewdoc/download?doi=10.1.1.14.9450&rep=rep1&type=pdf


Integer Optimizations
---------------------

Caching Small Integers
++++++++++++++++++++++

Similar to CPython, it is possible to enable caching of small integer objects to
not have to allocate all the time when doing simple arithmetic. Every time a new
integer object is created it is checked whether the integer is small enough to
be retrieved from the cache.

This option is disabled by default, you can enable this feature with the
:config:`objspace.std.withprebuiltint` option.

Integers as Tagged Pointers
+++++++++++++++++++++++++++

An even more aggressive way to save memory when using integers is "small int"
integer implementation. It is another integer implementation used for integers
that only needs 31 bits (or 63 bits on a 64 bit machine). These integers
are represented as tagged pointers by setting their lowest bits to distinguish
them from normal pointers. This completely avoids the boxing step, saving
time and memory.

You can enable this feature with the :config:`objspace.std.withsmallint` option.

Dictionary Optimizations
------------------------

Multi-Dicts
+++++++++++

Multi-dicts are a special implementation of dictionaries.  It became clear that
it is very useful to *change* the internal representation of an object during
its lifetime.  Multi-dicts are a general way to do that for dictionaries: they
provide generic support for the switching of internal representations for
dicts.

If you just enable multi-dicts, special representations for empty dictionaries,
for string-keyed dictionaries. In addition there are more specialized dictionary
implementations for various purposes (see below).

This is now the default implementation of dictionaries in the Python interpreter.

Sharing Dicts
+++++++++++++

Sharing dictionaries are a special representation used together with multidicts.
This dict representation is used only for instance dictionaries and tries to
make instance dictionaries use less memory (in fact, in the ideal case the
memory behaviour should be mostly like that of using __slots__).

The idea is the following: Most instances of the same class have very similar
attributes, and are even adding these keys to the dictionary in the same order
while ``__init__()`` is being executed. That means that all the dictionaries of
these instances look very similar: they have the same set of keys with different
values per instance. What sharing dicts do is store these common keys into a
common structure object and thus save the space in the individual instance
dicts:
the representation of the instance dict contains only a list of values.

A more advanced version of sharing dicts, called *map dicts,* is available
with the :config:`objspace.std.withmapdict` option.


List Optimizations
------------------

Range-Lists
+++++++++++

Range-lists solve the same problem that the ``xrange`` builtin solves poorly:
the problem that ``range`` allocates memory even if the resulting list is only
ever used for iterating over it. Range lists are a different implementation for
lists. They are created only as a result of a call to ``range``. As long as the
resulting list is used without being mutated, the list stores only the start, stop
and step of the range. Only when somebody mutates the list the actual list is
created. This gives the memory and speed behaviour of ``xrange`` and the generality
of use of ``range``, and makes ``xrange`` essentially useless.

You can enable this feature with the :config:`objspace.std.withrangelist`
option.


User Class Optimizations
------------------------


Method Caching
++++++++++++++

A method cache is introduced where the result of a method lookup
is stored (which involves potentially many lookups in the base classes of a
class). Entries in the method cache are stored using a hash computed from
the name being looked up, the call site (i.e. the bytecode object and
the current program counter), and a special "version" of the type where the
lookup happens (this version is incremented every time the type or one of its
base classes is changed). On subsequent lookups the cached version can be used,
as long as the instance did not shadow any of its classes attributes.

You can enable this feature with the :config:`objspace.std.withmethodcache`
option.

Interpreter Optimizations
=========================

Special Bytecodes
-----------------

.. _`lookup method call method`:

LOOKUP_METHOD & CALL_METHOD
+++++++++++++++++++++++++++

An unusual feature of Python's version of object oriented programming is the
concept of a "bound method".  While the concept is clean and powerful, the
allocation and initialization of the object is not without its performance cost.
We have implemented a pair of bytecodes that alleviate this cost.

For a given method call ``obj.meth(x, y)``, the standard bytecode looks like
this::

    LOAD_GLOBAL     obj      # push 'obj' on the stack
    LOAD_ATTR       meth     # read the 'meth' attribute out of 'obj'
    LOAD_GLOBAL     x        # push 'x' on the stack
    LOAD_GLOBAL     y        # push 'y' on the stack
    CALL_FUNCTION   2        # call the 'obj.meth' object with arguments x, y

We improved this by keeping method lookup separated from method call, unlike
some other approaches, but using the value stack as a cache instead of building
a temporary object.  We extended the bytecode compiler to (optionally) generate
the following code for ``obj.meth(x)``::

    LOAD_GLOBAL     obj
    LOOKUP_METHOD   meth
    LOAD_GLOBAL     x
    LOAD_GLOBAL     y
    CALL_METHOD     2

``LOOKUP_METHOD`` contains exactly the same attribute lookup logic as
``LOAD_ATTR`` - thus fully preserving semantics - but pushes two values onto the
stack instead of one.  These two values are an "inlined" version of the bound
method object: the *im_func* and *im_self*, i.e.  respectively the underlying
Python function object and a reference to ``obj``.  This is only possible when
the attribute actually refers to a function object from the class; when this is
not the case, ``LOOKUP_METHOD`` still pushes two values, but one *(im_func)* is
simply the regular result that ``LOAD_ATTR`` would have returned, and the other
*(im_self)* is a None placeholder.

After pushing the arguments, the layout of the stack in the above
example is as follows (the stack grows upwards):

+---------------------------------+
| ``y`` *(2nd arg)*               |
+---------------------------------+
| ``x`` *(1st arg)*               |
+---------------------------------+
| ``obj`` *(im_self)*             |
+---------------------------------+
| ``function object`` *(im_func)* |
+---------------------------------+

The ``CALL_METHOD N`` bytecode emulates a bound method call by
inspecting the *im_self* entry in the stack below the ``N`` arguments:
if it is not None, then it is considered to be an additional first
argument in the call to the *im_func* object from the stack.

You can enable this feature with the :config:`objspace.opcodes.CALL_METHOD`
option.

.. _`call likely builtin`:

CALL_LIKELY_BUILTIN
+++++++++++++++++++

A often heard "tip" for speeding up Python programs is to give an often used
builtin a local name, since local lookups are faster than lookups of builtins,
which involve doing two dictionary lookups: one in the globals dictionary and
one in the the builtins dictionary. PyPy approaches this problem at the
implementation level, with the introduction of the new ``CALL_LIKELY_BUILTIN``
bytecode. This bytecode is produced by the compiler for a call whose target is
the name of a builtin.  Since such a syntactic construct is very often actually
invoking the expected builtin at run-time, this information can be used to make
the call to the builtin directly, without going through any dictionary lookup.

However, it can occur that the name is shadowed by a global name from the
current module.  To catch this case, a special dictionary implementation for
multidicts is introduced, which is used for the dictionaries of modules. This
implementation keeps track which builtin name is shadowed by it.  The
``CALL_LIKELY_BUILTIN`` bytecode asks the dictionary whether it is shadowing the
builtin that is about to be called and asks the dictionary of ``__builtin__``
whether the original builtin was changed.  These two checks are cheaper than
full lookups.  In the common case, neither of these cases is true, so the
builtin can be directly invoked.

You can enable this feature with the
:config:`objspace.opcodes.CALL_LIKELY_BUILTIN` option.

.. more here?

Overall Effects
===============

The impact these various optimizations have on performance unsurprisingly
depends on the program being run.  Using the default multi-dict implementation that
simply special cases string-keyed dictionaries is a clear win on all benchmarks,
improving results by anything from 15-40 per cent.

Another optimization, or rather set of optimizations, that has a uniformly good
effect are the two 'method optimizations', i.e. the
method cache and the LOOKUP_METHOD and CALL_METHOD opcodes.  On a heavily
object-oriented benchmark (richards) they combine to give a speed-up of nearly
50%, and even on the extremely un-object-oriented pystone benchmark, the
improvement is over 20%.

When building pypy, all generally useful optimizations are turned on by default
unless you explicitly lower the translation optimization level with the
``--opt`` option.
