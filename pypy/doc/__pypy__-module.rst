.. comment: this document is very incomplete, should we generate
            it automatically?

The ``__pypy__`` module
=======================

The ``__pypy__`` module is the main entry point to special features provided
by PyPy's standard interpreter. Its content depends on :doc:`configuration options <config/index>`
which may add new functionality and functions whose existence or non-existence
indicates the presence of such features.


Generally available functionality
---------------------------------

 - ``internal_repr(obj)``: return the interpreter-level representation of an
   object.
 - ``bytebuffer(length)``: return a new read-write buffer of the given length.
   It works like a simplified array of characters (actually, depending on the
   configuration the ``array`` module internally uses this).
 - ``attach_gdb()``: start a GDB at the interpreter-level (or a PDB before translation).


Transparent Proxy Functionality
-------------------------------

If :ref:`transparent proxies <tproxy>` are enabled (with :config:`objspace.std.withtproxy`)
the following functions are put into ``__pypy__``:

 - ``tproxy(typ, controller)``: Return something that looks like it is of type
   typ. Its behaviour is completely controlled by the controller. See the docs
   about :ref:`transparent proxies <tproxy>` for detail.
 - ``get_tproxy_controller(obj)``: If obj is really a transparent proxy, return
   its controller. Otherwise return None.


Functionality available on py.py (not after translation)
--------------------------------------------------------

 - ``isfake(obj)``: returns True if ``obj`` is faked.
