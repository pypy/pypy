====================================
Differences between PyPy and CPython
====================================

This page documents the few differences and incompatibilities between
the PyPy Python interpreter and CPython.  Some of these differences
are "by design", since we think that there are cases in which the
behaviour of CPython is buggy, and we do not want to copy bugs.

Differences that are not listed here should be considered bugs of
PyPy.


Extension modules
-----------------

List of extension modules that we support:

* Supported as built-in modules (in `pypy/module/`_):

    __builtin__
    `__pypy__`_
    _ast
    _bisect
    _codecs
    _collections
    `_ffi`_
    _hashlib
    _io
    _locale
    _lsprof
    _md5
    `_minimal_curses`_
    _multiprocessing
    _random
    `_rawffi`_
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
    clr
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
    oracle
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

  When translated to Java or .NET, the list is smaller; see
  `pypy/config/pypyoption.py`_ for details.

  When translated on Windows, a few Unix-only modules are skipped,
  and the following module is built instead:

    _winreg

  Extra module with Stackless_ only:

    _stackless

* Supported by being rewritten in pure Python (possibly using ``ctypes``):
  see the `lib_pypy/`_ directory.  Examples of modules that we
  support this way: ``ctypes``, ``cPickle``, ``cmath``, ``dbm``, ``datetime``...
  Note that some modules are both in there and in the list above;
  by default, the built-in module is used (but can be disabled
  at translation time).

The extension modules (i.e. modules written in C, in the standard CPython)
that are neither mentioned above nor in `lib_pypy/`_ are not available in PyPy.
(You may have a chance to use them anyway with `cpyext`_.)

.. the nonstandard modules are listed below...
.. _`__pypy__`: __pypy__-module.html
.. _`_ffi`: ctypes-implementation.html
.. _`_rawffi`: ctypes-implementation.html
.. _`_minimal_curses`: config/objspace.usemodules._minimal_curses.html
.. _`cpyext`: http://morepypy.blogspot.com/2010/04/using-cpython-extension-modules-with.html
.. _Stackless: stackless.html


Differences related to garbage collection strategies
----------------------------------------------------

Most of the garbage collectors used or implemented by PyPy are not based on
reference counting, so the objects are not freed instantly when they are no
longer reachable.  The most obvious effect of this is that files are not
promptly closed when they go out of scope.  For files that are opened for
writing, data can be left sitting in their output buffers for a while, making
the on-disk file appear empty or truncated.

Fixing this is essentially not possible without forcing a
reference-counting approach to garbage collection.  The effect that you
get in CPython has clearly been described as a side-effect of the
implementation and not a language design decision: programs relying on
this are basically bogus.  It would anyway be insane to try to enforce
CPython's behavior in a language spec, given that it has no chance to be
adopted by Jython or IronPython (or any other port of Python to Java or
.NET, like PyPy itself).

This affects the precise time at which __del__ methods are called, which
is not reliable in PyPy (nor Jython nor IronPython).  It also means that
weak references may stay alive for a bit longer than expected.  This
makes "weak proxies" (as returned by ``weakref.proxy()``) somewhat less
useful: they will appear to stay alive for a bit longer in PyPy, and
suddenly they will really be dead, raising a ``ReferenceError`` on the
next access.  Any code that uses weak proxies must carefully catch such
``ReferenceError`` at any place that uses them.

There are a few extra implications for the difference in the GC.  Most
notably, if an object has a __del__, the __del__ is never called more
than once in PyPy; but CPython will call the same __del__ several times
if the object is resurrected and dies again.  The __del__ methods are
called in "the right" order if they are on objects pointing to each
other, as in CPython, but unlike CPython, if there is a dead cycle of
objects referencing each other, their __del__ methods are called anyway;
CPython would instead put them into the list ``garbage`` of the ``gc``
module.  More information is available on the blog `[1]`__ `[2]`__.

.. __: http://morepypy.blogspot.com/2008/02/python-finalizers-semantics-part-1.html
.. __: http://morepypy.blogspot.com/2008/02/python-finalizers-semantics-part-2.html

Using the default GC called ``minimark``, the built-in function ``id()``
works like it does in CPython.  With other GCs it returns numbers that
are not real addresses (because an object can move around several times)
and calling it a lot can lead to performance problem.

Note that if you have a long chain of objects, each with a reference to
the next one, and each with a __del__, PyPy's GC will perform badly.  On
the bright side, in most other cases, benchmarks have shown that PyPy's
GCs perform much better than CPython's.

Another difference is that if you add a ``__del__`` to an existing class it will
not be called::

    >>>> class A(object):
    ....     pass
    ....
    >>>> A.__del__ = lambda self: None
    __main__:1: RuntimeWarning: a __del__ method added to an existing type will not be called


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
In PyPy, they are generally always called, whereas not in
CPython.  For example, in PyPy, ``dict1.update(dict2)``
considers that ``dict2`` is just a general mapping object, and
will thus call overridden ``keys()``  and ``__getitem__()``
methods on it.  So the following code prints ``42`` on PyPy
but ``foo`` on CPython::

    >>>> class D(dict):
    ....     def __getitem__(self, key):
    ....         return 42
    ....
    >>>>
    >>>> d1 = {}
    >>>> d2 = D(a='foo')
    >>>> d1.update(d2)
    >>>> print d1['a']
    42


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


Miscellaneous
-------------

* ``sys.setrecursionlimit()`` is ignored (and not needed) on
  PyPy.  On CPython it would set the maximum number of nested
  calls that can occur before a RuntimeError is raised; on PyPy
  overflowing the stack also causes RuntimeErrors, but the limit
  is checked at a lower level.  (The limit is currently hard-coded
  at 768 KB, corresponding to roughly 1480 Python calls on
  Linux.)

* assignment to ``__class__`` is limited to the cases where it
  works on CPython 2.5.  On CPython 2.6 and 2.7 it works in a bit
  more cases, which are not supported by PyPy so far.  (If needed,
  it could be supported, but then it will likely work in many
  *more* case on PyPy than on CPython 2.6/2.7.)


.. include:: _ref.txt
