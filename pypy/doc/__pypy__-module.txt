=======================
The ``__pypy__`` module
=======================

The ``__pypy__`` module is the main entry point to special features provided
by PyPy's standard interpreter. Its content depends on `configuration options`_ 
which may add new functionality and functions whose existence or non-existence 
indicates the presence of such features. 

.. _`configuration options`: config/index.html

Generally available functionality
=================================

 - ``internal_repr(obj)``: return the interpreter-level representation of an
   object.
 - ``bytebuffer(length)``: return a new read-write buffer of the given length.
   It works like a simplified array of characters (actually, depending on the
   configuration the ``array`` module internally uses this).

Thunk Object Space Functionality
================================

When the thunk object space is used (choose with :config:`objspace.name`),
the following functions are put into ``__pypy__``:

 - ``thunk``
 - ``is_thunk``
 - ``become``
 - ``lazy``

Those are all described in the `interface section of the thunk object space
docs`_.

For explanations and examples see the `thunk object space docs`_.

.. _`thunk object space docs`: objspace-proxies.html#thunk
.. _`interface section of the thunk object space docs`: objspace-proxies.html#thunk-interface

Taint Object Space Functionality
================================

When the taint object space is used (choose with :config:`objspace.name`),
the following names are put into ``__pypy__``:

 - ``taint``
 - ``is_tainted``
 - ``untaint``
 - ``taint_atomic``
 - ``_taint_debug``
 - ``_taint_look``
 - ``TaintError``

Those are all described in the `interface section of the taint object space
docs`_.

For more detailed explanations and examples see the `taint object space docs`_.

.. _`taint object space docs`: objspace-proxies.html#taint
.. _`interface section of the taint object space docs`: objspace-proxies.html#taint-interface

Transparent Proxy Functionality
===============================

If `transparent proxies`_ are enabled (with :config:`objspace.std.withtproxy`)
the following functions are put into ``__pypy__``:

 - ``tproxy(typ, controller)``: Return something that looks like it is of type
   typ. Its behaviour is completely controlled by the controller. See the docs
   about `transparent proxies`_ for detail.

 - ``get_tproxy_controller(obj)``: If obj is really a transparent proxy, return
   its controller. Otherwise return None.

.. _`transparent proxies`: objspace-proxies.html#tproxy


Functionality available on py.py (not after translation)
========================================================

 - ``isfake(obj)``: returns True if ``obj`` is faked.

 - ``interp_pdb()``: start a pdb at interpreter-level.



