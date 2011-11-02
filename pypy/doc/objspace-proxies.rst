=================================
What PyPy can do for your objects
=================================

.. contents::



Thanks to the `Object Space`_ architecture, any feature that is
based on proxying, extending, changing or otherwise controlling the
behavior of all objects in a running program is easy to implement on
top of PyPy.

Here is what we have implemented so far, in historical order:

* *Thunk Object Space*: lazily computed objects, computing only when an
  operation is performed on them; lazy functions, computing their result
  only if and when needed; and a way to globally replace an object with
  another.

* *Dump Object Space*: dumps all operations performed on all the objects
  into a large log file.  For debugging your applications.

* *Transparent Proxies Extension*: adds new proxy objects to
  the Standard Object Space that enable applications to 
  control operations on application and builtin objects, 
  e.g lists, dictionaries, tracebacks. 

Which object space to use can be chosen with the :config:`objspace.name`
option.

.. _`Object Space`: objspace.html

.. _thunk:

The Thunk Object Space
======================

This small object space, meant as a nice example, wraps another object
space (e.g. the standard one) and adds two capabilities: lazily computed
objects, computed only when an operation is performed on them, and
"become", a more obscure feature which allows to completely and globally
replaces an object with another.

Example usage of lazily computed objects::

    $ py.py -o thunk
    >>>> from __pypy__ import thunk
    >>>> def f():
    ....    print 'computing...'
    ....    return 6*7
    ....
    >>>> x = thunk(f)
    >>>> x
    computing...
    42
    >>>> x
    42
    >>>> y = thunk(f)
    >>>> type(y)
    computing...
    <type 'int'>

Example of how one object can be instantly and globally replaced with
another::

    $ py.py -o thunk
    >>>> from __pypy__ import become
    >>>> x = object()
    >>>> lst = [1, 2, x, 4]
    >>>> become(x, 3)
    >>>> lst
    [1, 2, 3, 4]

There is also a decorator for functions whose result can be computed
lazily (the function appears to return a result, but it is not really
invoked before the result is used, if at all)::

    $ py.py -o thunk
    >>>> from __pypy__ import lazy
    >>>> @lazy
    .... def f(x):
    ....    print 'computing...'
    ....    return x * 100
    ....
    >>>> lst = [f(i) for i in range(10)]
    >>>> del lst[1:9]
    >>>> lst
    computing...
    computing...
    [0, 900]

Implementation
--------------

The implementation is short (see `pypy/objspace/thunk.py`_).  For the
purpose of ``become()``, it adds an internal field `w_thunkalias` to
each object, which is either None (in the common case) or a reference to
the object that this object was replaced with.  When any space operation
is invoked, the chain of ``w_thunkalias`` references is followed and the
underlying object space really operates on the new objects instead of
the old ones.

For the laziness part, the function ``thunk()`` returns an instance of a
new internal class ``W_Thunk`` which stores the user-supplied callable
and arguments.  When a space operation follows the ``w_thunkalias``
chains of objects, it special-cases ``W_Thunk``: it invokes the stored
callable if necessary to compute the real value and then stores it in
the ``w_thunkalias`` field of the ``W_Thunk``.  This has the effect of
replacing the latter with the real value.

.. _thunk-interface:

Interface
---------

In a PyPy running with (or translated with) the Thunk Object Space,
the ``__pypy__`` module exposes the following interface:

 * ``thunk(f, *args, **kwargs)``: returns something that behaves like the result
   of the call ``f(*args, **kwargs)`` but the call is done lazily.

 * ``is_thunk(obj)``: return True if ``obj`` is a thunk that is not computed
   yet.

 * ``become(obj1, obj2)``: globally replace ``obj1`` with ``obj2``.

 * ``lazy(callable)``: should be used as a function decorator - the decorated
   function behaves lazily: all calls to it return a thunk object.


.. _dump:

The Dump Object Space
=====================

When PyPy is run with (or translated with) the *Dump Object Space*, all
operations between objects are dumped to a file called
``pypy-space-dump``.  This should give a powerful way to debug
applications, but so far the dump can only be inspected in a text
editor; better browsing tools are needed before it becomes really useful.

Try::

    $ py.py -o dump
    >>>> 2+3
    5
    >>>> (exit py.py here)
    $ more pypy-space-dump

On my machine the ``add`` between 2 and 3 starts at line 3152 (!)  and
returns at line 3164.  All the rest is start-up, printing, and shutdown.


.. _tproxy:

Transparent Proxies
================================

PyPy's Transparent Proxies allow routing of operations on objects 
to a callable.  Application level code can customize objects without
interfering with the type system - ``type(proxied_list) is list`` holds true
when 'proxied_list' is a proxied built-in list - while
giving you full control on all operations that are performed on the
``proxied_list``.

See [D12.1]_ for more context, motivation and usage of transparent proxies. 

Example of the core mechanism 
-------------------------------------------

The following example proxies a list and will 
return ``42`` on any add operation to the list:: 

   $ py.py --objspace-std-withtproxy 
   >>>> from __pypy__ import tproxy
   >>>> def f(operation, *args, **kwargs):
   >>>>    if operation == '__add__':
   >>>>         return 42
   >>>>    raise AttributeError
   >>>>
   >>>> i = tproxy(list, f)
   >>>> type(i)
   list
   >>>> i + 3
   42

.. _`alternative object implementations`: interpreter-optimizations.html


Example of recording all operations on builtins
----------------------------------------------------

Suppose we want to have a list which stores all operations performed on
it for later analysis.  We can use the small `lib_pypy/tputil.py`_ module to help
with transparently proxying builtin instances::

   from tputil import make_proxy

   history = []
   def recorder(operation):
       history.append(operation) 
       return operation.delegate()

   >>>> l = make_proxy(recorder, obj=[])    
   >>>> type(l)
   list
   >>>> l.append(3)
   >>>> len(l)
   1
   >>>> len(history)
   2
   
``make_proxy(recorder, obj=[])`` creates a transparent list
proxy where we can delegate operations to in the ``recorder`` function. 
Calling ``type(l)`` does not lead to any operation being executed at all. 

Note that ``append`` shows up as ``__getattribute__`` and that ``type(lst)``
does not show up at all - the type is the only aspect of the instance which
the controller cannot change.

.. _`transparent proxy builtins`: 

Transparent Proxy PyPy builtins and support
-----------------------------------------------------------

If you are using the `--objspace-std-withtproxy`_ option 
the `__pypy__`_ module provides the following builtins: 

* ``tproxy(type, controller)``: returns a proxy object 
  representing the given type and forwarding all operations 
  on this type to the controller.  On each such operation
  ``controller(opname, *args, **kwargs)`` is invoked. 

* ``get_tproxy_controller(obj)``:  returns the responsible 
  controller for a given object.  For non-proxied objects
  ``None`` is returned.  

.. _`__pypy__`:  __pypy__-module.html 
.. _`--objspace-std-withtproxy`: config/objspace.std.withtproxy.html

.. _tputil: 

tputil helper module 
----------------------------

The `lib_pypy/tputil.py`_ module provides: 

* ``make_proxy(controller, type, obj)``: function which 
  creates a transparent proxy controlled by the given 
  'controller' callable.  The proxy will appear 
  as a completely regular instance of the given 
  type but all operations on it are send to the 
  specified controller - which receives a
  ProxyOperation instance on each such operation.  
  A non-specified type will default to type(obj) if 
  `obj` was specified. 

  ProxyOperation instances have the following attributes: 

    `proxyobj`: the transparent proxy object of this operation. 

    `opname`: the operation name of this operation 

    `args`: positional arguments for this operation 

    `kwargs`: keyword arguments for this operation 

    `obj`: (if provided to `make_proxy`): a concrete object

  If you have specified a concrete object instance `obj` 
  to your `make_proxy` invocation, you may call 
  ``proxyoperation.delegate()`` to delegate the operation 
  to this object instance. 

Further points of interest
---------------------------

A lot of tasks could be performed using transparent proxies, including,
but not limited to:

* Remote versions of objects, on which we can directly perform operations
  (think about transparent distribution)

* Access to persistent storage such as a database (imagine an
  SQL object mapper which looks like a real object)

* Access to external data structures, such as other languages, as normal
  objects (of course some operations could raise exceptions, but 
  since they are purely done on application level, that is not real problem)

Implementation Notes
-----------------------------

PyPy's standard object space allows to internally have multiple
implementations of a type and change the implementation at run
time while application level code consistently sees the exact 
same type and object.  Multiple performance optimizations using 
this features are already implemented: see the document
about `alternative object implementations`_. Transparent
Proxies use the architecture to provide control back 
to application level code. 

Transparent proxies are implemented on top of the `standard object
space`_, in `pypy/objspace/std/proxy_helpers.py`_, `pypy/objspace/std/proxyobject.py`_ and
`pypy/objspace/std/transparent.py`_.  To use them you will need to pass a
`--objspace-std-withtproxy`_ option to ``py.py`` or
``translate.py``.  This registers implementations named
``W_TransparentXxx`` - which usually correspond to an
appropriate ``W_XxxObject`` - and includes some interpreter hacks
for objects that are too close to the interpreter to be
implemented in the std objspace. The types of objects that can
be proxied this way are user created classes & functions,
lists, dicts, exceptions, tracebacks and frames.

.. _`standard object space`: objspace.html#the-standard-object-space

.. [D12.1] `High-Level Backends and Interpreter Feature Prototypes`, PyPy
           EU-Report, 2007, http://codespeak.net/pypy/extradoc/eu-report/D12.1_H-L-Backends_and_Feature_Prototypes-2007-03-22.pdf

.. include:: _ref.txt
