Differences between PyPy and CPython
====================================

This page documents the few differences and incompatibilities between
the PyPy Python interpreter and CPython.  Some of these differences
are "by design", since we think that there are cases in which the
behaviour of CPython is buggy, and we do not want to copy bugs.

Differences that are not listed here should be considered bugs of
PyPy.


.. _extension-modules:

Extension modules
-----------------

List of extension modules that we support:

* Supported as built-in modules (in :source:`pypy/module/`):

    __builtin__
    :doc:`__pypy__ <__pypy__-module>`
    _ast
    _codecs
    _collections
    :doc:`_continuation <stackless>`
    :doc:`_ffi <discussion/ctypes-implementation>`
    _hashlib
    _io
    _locale
    _lsprof
    _md5
    :doc:`_minimal_curses <config/objspace.usemodules._minimal_curses>`
    _multiprocessing
    _random
    :doc:`_rawffi <discussion/ctypes-implementation>`
    _sha
    _socket
    _sre
    _ssl
    _warnings
    _weakref
    _winreg
    array
    binascii
    bz2
    cStringIO
    cmath
    `cpyext`_
    crypt
    errno
    exceptions
    fcntl
    gc
    imp
    itertools
    marshal
    math
    mmap
    operator
    parser
    posix
    pyexpat
    select
    signal
    struct
    symbol
    sys
    termios
    thread
    time
    token
    unicodedata
    zipimport
    zlib

  When translated on Windows, a few Unix-only modules are skipped,
  and the following module is built instead:

    _winreg

* Supported by being rewritten in pure Python (possibly using ``cffi``):
  see the :source:`lib_pypy/` directory.  Examples of modules that we
  support this way: ``ctypes``, ``cPickle``, ``cmath``, ``dbm``, ``datetime``...
  Note that some modules are both in there and in the list above;
  by default, the built-in module is used (but can be disabled
  at translation time).

The extension modules (i.e. modules written in C, in the standard CPython)
that are neither mentioned above nor in :source:`lib_pypy/` are not available in PyPy.
(You may have a chance to use them anyway with `cpyext`_.)

.. _cpyext: http://morepypy.blogspot.com/2010/04/using-cpython-extension-modules-with.html


Differences related to garbage collection strategies
----------------------------------------------------

The garbage collectors used or implemented by PyPy are not based on
reference counting, so the objects are not freed instantly when they are no
longer reachable.  The most obvious effect of this is that files are not
promptly closed when they go out of scope.  For files that are opened for
writing, data can be left sitting in their output buffers for a while, making
the on-disk file appear empty or truncated.  Moreover, you might reach your
OS's limit on the number of concurrently opened files.

Fixing this is essentially impossible without forcing a
reference-counting approach to garbage collection.  The effect that you
get in CPython has clearly been described as a side-effect of the
implementation and not a language design decision: programs relying on
this are basically bogus.  It would anyway be insane to try to enforce
CPython's behavior in a language spec, given that it has no chance to be
adopted by Jython or IronPython (or any other port of Python to Java or
.NET).

Even the naive idea of forcing a full GC when we're getting dangerously
close to the OS's limit can be very bad in some cases.  If your program
leaks open files heavily, then it would work, but force a complete GC
cycle every n'th leaked file.  The value of n is a constant, but the
program can take an arbitrary amount of memory, which makes a complete
GC cycle arbitrarily long.  The end result is that PyPy would spend an
arbitrarily large fraction of its run time in the GC --- slowing down
the actual execution, not by 10% nor 100% nor 1000% but by essentially
any factor.

To the best of our knowledge this problem has no better solution than
fixing the programs.  If it occurs in 3rd-party code, this means going
to the authors and explaining the problem to them: they need to close
their open files in order to run on any non-CPython-based implementation
of Python.

---------------------------------

Here are some more technical details.  This issue affects the precise
time at which ``__del__`` methods are called, which
is not reliable in PyPy (nor Jython nor IronPython).  It also means that
weak references may stay alive for a bit longer than expected.  This
makes "weak proxies" (as returned by ``weakref.proxy()``) somewhat less
useful: they will appear to stay alive for a bit longer in PyPy, and
suddenly they will really be dead, raising a ``ReferenceError`` on the
next access.  Any code that uses weak proxies must carefully catch such
``ReferenceError`` at any place that uses them.  (Or, better yet, don't use
``weakref.proxy()`` at all; use ``weakref.ref()``.)

There are a few extra implications from the difference in the GC.  Most
notably, if an object has a ``__del__``, the ``__del__`` is never called more
than once in PyPy; but CPython will call the same ``__del__`` several times
if the object is resurrected and dies again.  The ``__del__`` methods are
called in "the right" order if they are on objects pointing to each
other, as in CPython, but unlike CPython, if there is a dead cycle of
objects referencing each other, their ``__del__`` methods are called anyway;
CPython would instead put them into the list ``garbage`` of the ``gc``
module.  More information is available on the blog `[1]`__ `[2]`__.

.. __: http://morepypy.blogspot.com/2008/02/python-finalizers-semantics-part-1.html
.. __: http://morepypy.blogspot.com/2008/02/python-finalizers-semantics-part-2.html

Note that this difference might show up indirectly in some cases.  For
example, a generator left pending in the middle is --- again ---
garbage-collected later in PyPy than in CPython.  You can see the
difference if the ``yield`` keyword it is suspended at is itself
enclosed in a ``try:`` or a ``with:`` block.  This shows up for example
as `issue 736`__.

.. __: http://bugs.pypy.org/issue736

Using the default GC (called ``minimark``), the built-in function ``id()``
works like it does in CPython.  With other GCs it returns numbers that
are not real addresses (because an object can move around several times)
and calling it a lot can lead to performance problem.

Note that if you have a long chain of objects, each with a reference to
the next one, and each with a ``__del__``, PyPy's GC will perform badly.  On
the bright side, in most other cases, benchmarks have shown that PyPy's
GCs perform much better than CPython's.

Another difference is that if you add a ``__del__`` to an existing class it will
not be called::

    >>>> class A(object):
    ....     pass
    ....
    >>>> A.__del__ = lambda self: None
    __main__:1: RuntimeWarning: a __del__ method added to an existing type will not be called

Even more obscure: the same is true, for old-style classes, if you attach
the ``__del__`` to an instance (even in CPython this does not work with
new-style classes).  You get a RuntimeWarning in PyPy.  To fix these cases
just make sure there is a ``__del__`` method in the class to start with
(even containing only ``pass``; replacing or overriding it later works fine).


Subclasses of built-in types
----------------------------

Officially, CPython has no rule at all for when exactly
overridden method of subclasses of built-in types get
implicitly called or not.  As an approximation, these methods
are never called by other built-in methods of the same object.
For example, an overridden ``__getitem__()`` in a subclass of
``dict`` will not be called by e.g. the built-in ``get()``
method.

The above is true both in CPython and in PyPy.  Differences
can occur about whether a built-in function or method will
call an overridden method of *another* object than ``self``.
In PyPy, they are often called in cases where CPython would not.
Two examples::

    class D(dict):
        def __getitem__(self, key):
            return "%r from D" % (key,)

    class A(object):
        pass

    a = A()
    a.__dict__ = D()
    a.foo = "a's own foo"
    print a.foo
    # CPython => a's own foo
    # PyPy => 'foo' from D

    glob = D(foo="base item")
    loc = {}
    exec "print foo" in glob, loc
    # CPython => base item
    # PyPy => 'foo' from D


Mutating classes of objects which are already used as dictionary keys
---------------------------------------------------------------------

Consider the following snippet of code::

    class X(object):
        pass

    def __evil_eq__(self, other):
        print 'hello world'
        return False

    def evil(y):
        d = {x(): 1}
        X.__eq__ = __evil_eq__
        d[y] # might trigger a call to __eq__?

In CPython, __evil_eq__ **might** be called, although there is no way to write
a test which reliably calls it.  It happens if ``y is not x`` and ``hash(y) ==
hash(x)``, where ``hash(x)`` is computed when ``x`` is inserted into the
dictionary.  If **by chance** the condition is satisfied, then ``__evil_eq__``
is called.

PyPy uses a special strategy to optimize dictionaries whose keys are instances
of user-defined classes which do not override the default ``__hash__``,
``__eq__`` and ``__cmp__``: when using this strategy, ``__eq__`` and
``__cmp__`` are never called, but instead the lookup is done by identity, so
in the case above it is guaranteed that ``__eq__`` won't be called.

Note that in all other cases (e.g., if you have a custom ``__hash__`` and
``__eq__`` in ``y``) the behavior is exactly the same as CPython.


Ignored exceptions
-----------------------

In many corner cases, CPython can silently swallow exceptions.
The precise list of when this occurs is rather long, even
though most cases are very uncommon.  The most well-known
places are custom rich comparison methods (like \_\_eq\_\_);
dictionary lookup; calls to some built-in functions like
isinstance().

Unless this behavior is clearly present by design and
documented as such (as e.g. for hasattr()), in most cases PyPy
lets the exception propagate instead.


Object Identity of Primitive Values, ``is`` and ``id``
-------------------------------------------------------

Object identity of primitive values works by value equality, not by identity of
the wrapper. This means that ``x + 1 is x + 1`` is always true, for arbitrary
integers ``x``. The rule applies for the following types:

 - ``int``

 - ``float``

 - ``long``

 - ``complex``

This change requires some changes to ``id`` as well. ``id`` fulfills the
following condition: ``x is y <=> id(x) == id(y)``. Therefore ``id`` of the
above types will return a value that is computed from the argument, and can
thus be larger than ``sys.maxint`` (i.e. it can be an arbitrary long).

Notably missing from the list above are ``str`` and ``unicode``.  If your
code relies on comparing strings with ``is``, then it might break in PyPy.


Miscellaneous
-------------

* Hash randomization (``-R``) is ignored in PyPy.  As documented in
  http://bugs.python.org/issue14621, some of us believe it has no
  purpose in CPython either.

* ``sys.setrecursionlimit(n)`` sets the limit only approximately,
  by setting the usable stack space to ``n * 768`` bytes.  On Linux,
  depending on the compiler settings, the default of 768KB is enough
  for about 1400 calls.

* since the implementation of dictionary is different, the exact number
  which ``__hash__`` and ``__eq__`` are called is different. Since CPython
  does not give any specific guarantees either, don't rely on it.

* assignment to ``__class__`` is limited to the cases where it
  works on CPython 2.5.  On CPython 2.6 and 2.7 it works in a bit
  more cases, which are not supported by PyPy so far.  (If needed,
  it could be supported, but then it will likely work in many
  *more* case on PyPy than on CPython 2.6/2.7.)

* the ``__builtins__`` name is always referencing the ``__builtin__`` module,
  never a dictionary as it sometimes is in CPython. Assigning to
  ``__builtins__`` has no effect.

* directly calling the internal magic methods of a few built-in types
  with invalid arguments may have a slightly different result.  For
  example, ``[].__add__(None)`` and ``(2).__add__(None)`` both return
  ``NotImplemented`` on PyPy; on CPython, only the latter does, and the
  former raises ``TypeError``.  (Of course, ``[]+None`` and ``2+None``
  both raise ``TypeError`` everywhere.)  This difference is an
  implementation detail that shows up because of internal C-level slots
  that PyPy does not have.

* on CPython, ``[].__add__`` is a ``method-wrapper``, and
  ``list.__add__`` is a ``slot wrapper``.  On PyPy these are normal
  bound or unbound method objects.  This can occasionally confuse some
  tools that inspect built-in types.  For example, the standard
  library ``inspect`` module has a function ``ismethod()`` that returns
  True on unbound method objects but False on method-wrappers or slot
  wrappers.  On PyPy we can't tell the difference, so
  ``ismethod([].__add__) == ismethod(list.__add__) == True``.

* the ``__dict__`` attribute of new-style classes returns a normal dict, as
  opposed to a dict proxy like in CPython. Mutating the dict will change the
  type and vice versa. For builtin types, a dictionary will be returned that
  cannot be changed (but still looks and behaves like a normal dictionary).

* PyPy prints a random line from past #pypy IRC topics at startup in
  interactive mode. In a released version, this behaviour is supressed, but
  setting the environment variable PYPY_IRC_TOPIC will bring it back. Note that
  downstream package providers have been known to totally disable this feature.
