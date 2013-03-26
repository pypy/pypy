=================================
What PyPy can do for your objects
=================================

.. contents::



Thanks to the `Object Space`_ architecture, any feature that is
based on proxying, extending, changing or otherwise controlling the
behavior of all objects in a running program is easy to implement on
top of PyPy.

Here is what we have implemented so far, in historical order:

* *Dump Object Space*: dumps all operations performed on all the objects
  into a large log file.  For debugging your applications.

* *Transparent Proxies Extension*: adds new proxy objects to
  the Standard Object Space that enable applications to
  control operations on application and builtin objects,
  e.g lists, dictionaries, tracebacks.

.. _`Object Space`: objspace.html
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
