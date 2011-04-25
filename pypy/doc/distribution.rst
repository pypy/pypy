.. include:: needswork.rst

=============================
lib_pypy/distributed features
=============================

The 'distributed' library is an attempt to provide transparent, lazy
access to remote objects. This is accomplished using
`transparent proxies`_ and in application level code (so as a pure
python module).

The implementation uses an RPC-like protocol, which accesses
only members of objects, rather than whole objects. This means it
does not rely on objects being pickleable, nor on having the same
source code available on both sides. On each call, only the members
that are used on the client side are retrieved, objects which
are not used are merely references to their remote counterparts.

As an example, let's imagine we have a remote object, locally available
under the name `x`. Now we call::

    >>>> x.foo(1, [1,2,3], y)

where y is some instance of a local, user-created class.

Under water, x.\_\_getattribute\_\_ is called, with argument 'foo'. In the
\_\_getattribute\_\_ implementation, the 'foo' attribute is requested, and the
remote side replies by providing a bound method. On the client this bound
method appears as a remote reference: this reference is called with a remote
reference to x as self, the integer 1 which is copied as a primitive type, a
reference to a list and a reference to y. The remote side receives this call,
processes it as a call to the bound method x.foo, where 'x' is resolved as a
local object, 1 as an immutable primitive, [1,2,3] as a reference to a mutable
primitive and y as a reference to a remote object. If the type of y is not
known on the remote side, it is faked with just about enough shape (XXX?!?) to
be able to perform the required operations.  The contents of the list are
retrieved when they're needed.

An advantage of this approach is that a user can have remote references to
internal interpreter types, like frames, code objects and tracebacks. In a demo
directory there is an example of using this to attach pdb.post\_mortem() to a
remote traceback. Another advantage is that there's a minimal amount of data
transferred over the network. On the other hand, there are a large amount of
packages sent to the remote side - hopefully this will be improved in future.

The 'distributed' lib is uses an abstract network layer, which means you
can provide custom communication channels just by implementing
two functions that send and receive marshallable objects (no pickle needed!).

Exact rules of copying
----------------------

- Immutable primitives are always transferred

- Mutable primitives are transferred as a reference, but several operations
  (like iter()) force them to be transferred fully

- Builtin exceptions are transferred by name

- User objects are always faked on the other side, with enough shape
  transferred

XXX finish, basic interface, example, build some stuff on top of greenlets

Related work comparison
-----------------------

There are a lot of attempts to incorporate RPC mechanism into
Python, some of them are listed below:

* `Pyro`_ - Pyro stands for PYthon Remote Objects, it's a mechanism of
  implementing remotely accessible objects in pure python (without modifying
  interpreter). This is only a remote method call implementation, with
  all limitations, so:

  - No attribute access

  - Arguments of calls must be pickleable on one side and unpickleable on
    remote side, which means they must share source code, they do not
    become remote references

  - Exported objects must inherit from specific class and follow certain
    standards, like \_\_init\_\_ shape.

  - Remote tracebacks only as strings

  - Remote calls usually invokes new threads

* XMLRPC - There are several implementations of xmlrpc protocol in Python,
  one even in the standard library. Xmlrpc is cross-language, cross-platform
  protocol of communication, which implies great flexibility of tools to
  choose, but also implies several limitations, like:

  - No remote tracebacks

  - Only simple types to be passed as function arguments

* Twisted Perspective Broker

  - involves twisted, which ties user to network stack/programming style

  - event driven programming (might be good, might be bad, but it's fixed)

  - copies object (by pickling), but provides sophisticated layer of
    caching to avoid multiple copies of the same object.

  - two way RPC (unlike Pyro)

  - also heavy restrictions on objects - they must subclass certain class

.. _`Pyro`: http://pyro.sourceforge.net/
.. _`transparent proxies`: objspace-proxies.html#tproxy
