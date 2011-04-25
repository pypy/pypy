.. XXX anto, do we still need this?

==============================================
Integration of PyPy with host Virtual Machines
==============================================

This document is based on the discussion I had with Samuele during the
Duesseldorf sprint. It's not much more than random thoughts -- to be
reviewed!

Terminology disclaimer: both PyPy and .NET have the concept of
"wrapped" or "boxed" objects. To avoid confusion I will use "wrapping"
on the PyPy side and "boxing" on the .NET side.

General idea
============

The goal is to find a way to efficiently integrate the PyPy
interpreter with the hosting environment such as .NET. What we would
like to do includes but it's not limited to:

  - calling .NET methods and instantiate .NET classes from Python

  - subclass a .NET class from Python

  - handle native .NET objects as transparently as possible

  - automatically apply obvious Python <--> .NET conversions when
    crossing the borders (e.g. integers, string, etc.)

One possible solution is the "proxy" approach, in which we manually
(un)wrap/(un)box all the objects when they cross the border.

Example
-------

  ::

    public static int foo(int x) { return x}

    >>>> from somewhere import foo
    >>>> print foo(42)

In this case we need to take the intval field of W_IntObject, box it
to .NET System.Int32, call foo using reflection, then unbox the return
value and reconstruct a new (or reuse an existing one) W_IntObject.

The other approach
------------------

The general idea to solve handle this problem is to split the
"stateful" and "behavioral" parts of wrapped objects, and use already
boxed values for storing the state.

This way when we cross the Python --> .NET border we can just throw
away the behavioral part; when crossing .NET --> Python we have to
find the correct behavioral part for that kind of boxed object and
reconstruct the pair.


Split state and behaviour in the flowgraphs
===========================================

The idea is to write a graph transformation that takes an usual
ootyped flowgraph and split the classes and objects we want into a
stateful part and a behavioral part.

We need to introduce the new ootypesystem type ``Pair``: it acts like
a Record but it hasn't its own identity: the id of the Pair is the id
of its first member.

  XXX about ``Pair``: I'm not sure this is totally right. It means
  that an object can change identity simply by changing the value of a
  field???  Maybe we could add the constraint that the "id" field
  can't be modified after initialization (but it's not easy to
  enforce).

  XXX-2 about ``Pair``: how to implement it in the backends? One
  possibility is to use "struct-like" types if available (as in
  .NET). But in this case it's hard to implement methods/functions
  that modify the state of the object (such as __init__, usually). The
  other possibility is to use a reference type (i.e., a class), but in
  this case there will be a gap between the RPython identity (in which
  two Pairs with the same state are indistinguishable) and the .NET
  identity (in which the two objects will have a different identity,
  of course).

Step 1: RPython source code
---------------------------

  ::

    class W_IntObject:
        def __init__(self, intval):
            self.intval = intval
    
        def foo(self, x):
            return self.intval + x

    def bar():
        x = W_IntObject(41)
        return x.foo(1)


Step 2: RTyping
---------------

Sometimes the following examples are not 100% accurate for the sake of
simplicity (e.g: we directly list the type of methods instead of the
ootype._meth instances that contains it).

Low level types

  ::

    W_IntObject = Instance(
        "W_IntObject",                   # name
        ootype.OBJECT,                   # base class
        {"intval": (Signed, 0)},         # attributes
        {"foo": Meth([Signed], Signed)}  # methods
    )


Prebuilt constants (referred by name in the flowgraphs)

  ::

    W_IntObject_meta_pbc = (...)
    W_IntObject.__init__ = (static method pbc - see below for the graph)


Flowgraphs

  ::

    bar() {
      1.    x = new(W_IntObject)
      2.    oosetfield(x, "meta", W_IntObject_meta_pbc)
      3.    direct_call(W_IntObject.__init__, x, 41)
      4.    result = oosend("foo", x, 1)
      5.    return result
    }

    W_IntObject.__init__(W_IntObject self, Signed intval) {
      1.    oosetfield(self, "intval", intval)
    }

    W_IntObject.foo(W_IntObject self, Signed x) {
      1.    value = oogetfield(self, "value")
      2.    result = int_add(value, x)
      3.    return result
    }

Step 3: Transformation
----------------------

This step is done before the backend plays any role, but it's still
driven by its need, because at this time we want a mapping that tell
us what classes to split and how (i.e., which boxed value we want to
use).

Let's suppose we want to map W_IntObject.intvalue to the .NET boxed
``System.Int32``. This is possible just because W_IntObject contains
only one field. Note that the "meta" field inherited from
ootype.OBJECT is special-cased because we know that it will never
change, so we can store it in the behaviour.


Low level types

  ::

    W_IntObject_bhvr = Instance(
        "W_IntObject_bhvr",
        ootype.OBJECT,
        {},                                               # no more fields!
        {"foo": Meth([W_IntObject_pair, Signed], Signed)} # the Pair is also explicitly passed
    )

    W_IntObject_pair = Pair(
        ("value", (System.Int32, 0)),  # (name, (TYPE, default))
        ("behaviour", (W_IntObject_bhvr, W_IntObject_bhvr_pbc))
    )


Prebuilt constants

  ::

    W_IntObject_meta_pbc = (...)
    W_IntObject.__init__ = (static method pbc - see below for the graph)
    W_IntObject_bhvr_pbc = new(W_IntObject_bhvr); W_IntObject_bhvr_pbc.meta = W_IntObject_meta_pbc
    W_IntObject_value_default = new System.Int32(0)


Flowgraphs

  ::

    bar() {
      1.    x = new(W_IntObject_pair) # the behaviour has been already set because
                                      # it's the default value of the field

      2.    # skipped (meta is already set in the W_IntObject_bhvr_pbc)

      3.    direct_call(W_IntObject.__init__, x, 41)

      4.    bhvr = oogetfield(x, "behaviour")
            result = oosend("foo", bhvr, x, 1) # note that "x" is explicitly passed to foo

      5.    return result
    }

    W_IntObject.__init__(W_IntObjectPair self, Signed value) {
      1.    boxed = clibox(value)             # boxed is of type System.Int32
            oosetfield(self, "value", boxed)
    }

    W_IntObject.foo(W_IntObject_bhvr bhvr, W_IntObject_pair self, Signed x) {
      1.    boxed = oogetfield(self, "value")
            value = unbox(boxed, Signed)

      2.    result = int_add(value, x)

      3.    return result
    }


Inheritance
-----------

Apply the transformation to a whole class (sub)hierarchy is a bit more
complex. Basically we want to mimic the same hierarchy also on the
``Pair``\s, but we have to fight the VM limitations. In .NET for
example, we can't have "covariant fields"::

  class Base {
        public Base field;
  }

  class Derived: Base {
        public Derived field;
  }

A solution is to use only kind of ``Pair``, whose ``value`` and
``behaviour`` type are of the most precise type that can hold all the
values needed by the subclasses::

   class W_Object: pass
   class W_IntObject(W_Object): ...
   class W_StringObject(W_Object): ...

   ...

   W_Object_pair = Pair(System.Object, W_Object_bhvr)

Where ``System.Object`` is of course the most precise type that can
hold both ``System.Int32`` and ``System.String``.

This means that the low level type of all the ``W_Object`` subclasses
will be ``W_Object_pair``, but it also means that we will need to
insert the appropriate downcasts every time we want to access its
fields. I'm not sure how much this can impact performances.


