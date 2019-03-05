.. comment: this document may get out of synch with the code, but to generate
    it automatically we would need to use pypy to run sphinx-build

The ``__pypy__`` module
=======================

The ``__pypy__`` module is the main entry point to special features provided
by PyPy's standard interpreter. Its content depends on :doc:`configuration
options <config/index>` which may add new functionality and functions whose
existence or non-existence indicates the presence of such features. These are
generally used for compatibility when writing pure python modules that in
CPython are written in C. Not available in CPython, and so must be used inside a
``if platform.python_implementation == 'PyPy'`` block or otherwise hidden from
the CPython interpreter.


Generally available functionality
---------------------------------

  - ``internal_repr(obj)``: return the interpreter-level representation of an
    object.
  - ``bytebuffer(length)``: return a new read-write buffer of the given length.
    It works like a simplified array of characters (actually, depending on the
    configuration the ``array`` module internally uses this).

  - ``attach_gdb()``: start a GDB at the interpreter-level (or a PDB before translation).

 - ``newmemoryview(buffer, itemsize, format, shape=None, strides=None)``:
   create a `memoryview` instance with the data from ``buffer`` and the
   specified itemsize, format, and optional shape and strides.

 - ``bufferable``: a base class that must override the
   ``__buffer__(self, flags)`` method. This method should return a memoryview
   instance of the class instance. It is called by the C-API's ``tp_as_buffer.
   bf_getbuffer``.
   
  - ``debug_stop``
  - ``debug_print``
  - ``debug_print_once``
  - ``debug_flush``
  - ``debug_read_timestamp``
  - ``debug_get_timestamp_unit``

  - ``builtinify(func)``: To implement at app-level modules that are, in CPython,
    implemented in C: this decorator protects a function from being ever bound
    like a method.  Useful because some tests do things like put a "built-in"
    function on a class and access it via the instance.

  - ``hidden_applevel(func)``: Decorator that hides a function's frame from
    app-level

  - ``get_hidden_tb()``: Return the traceback of the current exception being
    handled by a frame hidden from applevel.

  - ``lookup_special(obj, meth)``: Lookup up a special method on an object.
  - ``do_what_I_mean``

  - ``resizelist_hint(...)``: Reallocate the underlying storage of the argument
    list to sizehint

  - ``newlist_hint(...)``: Create a new empty list that has an underlying
    storage of length sizehint

  - ``add_memory_pressure(bytes)``: Add memory pressure of estimate bytes.
    Useful when calling a C function that internally allocates a big chunk of
    memory. This instructs the GC to garbage collect sooner than it would
    otherwise.

  - ``newdict(type)``: Create a normal dict with a special implementation
    strategy. ``type`` is a string and can be:

    * ``"module"`` - equivalent to ``some_module.__dict__``

    * ``"instance"`` - equivalent to an instance dict with a not-changing-much
      set of keys

    * ``"kwargs"`` - keyword args dict equivalent of what you get from
      ``**kwargs`` in a function, optimized for passing around

    * ``"strdict"`` - string-key only dict. This one should be chosen
      automatically

  - ``reversed_dict``: Enumerate the keys in a dictionary object in reversed
    order.  This is a ``__pypy__`` function instead of being simply done by
    calling reversed(), for CPython compatibility: dictionaries are ordered in
    PyPY but not in Cpython2.7.  You should use the collections.OrderedDict
    class for cases where ordering is important. That class implements
    ``__reversed__`` by calling __pypy__.reversed_dict()

  - ``dict_popitem_first``: Interp-level implementation of
    ``OrderedDict.popitem(last=False)``.

  - ``delitem_if_value_is`` Atomic equivalent to: ``if dict.get(key) is value:
    del dict[key]``.

    SPECIAL USE CASES ONLY!  Avoid using on dicts which are specialized,
    e.g. to ``int`` or ``str`` keys, because it switches to the object
    strategy. Also, the ``is`` operation is really pointer equality, so avoid
    using it if ``value`` is an immutable object like ``int`` or ``str``.

  - ``move_to_end``: Move the key in a dictionary object into the first or last
    position. This is used in Python 3.x to implement ``OrderedDict.move_to_end()``.

  - ``strategy(dict or list or set)``: Return the underlying strategy currently
    used by the object

  - ``specialized_zip_2_lists``
  - ``locals_to_fast``
  - ``set_code_callback``
  - ``save_module_content_for_future_reload``
  - ``decode_long``
  - ``side_effects_ok``: For use with the reverse-debugger: this function
    normally returns True, but will return False if we are evaluating a
    debugging command like a watchpoint.  You are responsible for not doing any
    side effect at all (including no caching) when evaluating watchpoints. This
    function is meant to help a bit---you can write::

        if not __pypy__.side_effects_ok():
            skip the caching logic

    inside getter methods or properties, to make them usable from
    watchpoints.  Note that you need to re-run ``REVDB=.. pypy``
    after changing the Python code.

  - ``stack_almost_full``: Return True if the stack is more than 15/16th full.
  - ``pyos_inputhook``: Call PyOS_InputHook() from the CPython C API
  - ``os.real_getenv(...)`` gets OS environment variables skipping python code
  - ``_pypydatetime`` provides base classes with correct C API interactions for
    the pure-python ``datetime`` stdlib module

Fast String Concatenation
-------------------------
Rather than in-place concatenation ``+=``, use these to enable fast, minimal
copy, string building.

  - ``builders.StringBuilder``
  - ``builders.UnicodeBuilder``

Transparent Proxy Functionality
-------------------------------

If :ref:`transparent proxies <tproxy>` are enabled (with :config:`objspace.std.withtproxy`)
the following functions are put into ``__pypy__``:

 - ``tproxy(typ, controller)``: Return something that looks like it is of type
   typ. Its behaviour is completely controlled by the controller. See the docs
   about :ref:`transparent proxies <tproxy>` for detail.
 - ``get_tproxy_controller(obj)``: If obj is really a transparent proxy, return
   its controller. Otherwise return None.


Additional Clocks for Timing
----------------------------
The ``time`` submodule exposes the platform-dependent clock types such as
``CLOCK_BOOTTIME``, ``CLOCK_MONOTONIC``, ``CLOCK_MONOTONIC_COARSE``,
``CLOCK_MONOTONIC_RAW`` and two functions:

  - ``clock_gettime(m)`` which returns the clock type time in seconds and
  - ``clock_getres(m)`` which returns the clock resolution in seconds.

Extended Signal Handling
------------------------
``thread.signals_enbaled`` is a context manager to use in non-main threads.
    enables receiving signals in a "with" statement.  More precisely, if a
    signal is received by the process, then the signal handler might be
    called either in the main thread (as usual) or within another thread
    that is within a "with signals_enabled:".  This other thread should be
    ready to handle unexpected exceptions that the signal handler might
    raise --- notably KeyboardInterrupt.

Integer Operations with Overflow
--------------------------------
  - ``intop`` provides a module with integer operations that have
    two-complement overflow behaviour instead of overflowing to longs

Functionality available on py.py (not after translation)
--------------------------------------------------------

 - ``isfake(obj)``: returns True if ``obj`` is faked.
