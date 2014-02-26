
PyPy has a very minimal and a very strange embedding interface, based on
the usage of `cffi`_ and the philosophy that Python is a better language in C.
It was developed in collaboration with Roberto De Ioris from the `uwsgi`_
project. The `PyPy uwsgi plugin`_ is a good example of usage of such interface.

The first thing that you need, that we plan to change in the future, is to
compile PyPy yourself with an option ``--shared``. Consult the
`how to compile PyPy`_ doc for details. That should result in ``libpypy.so``
or ``pypy.dll`` file or something similar, depending on your platform. Consult
your platform specification for details.

The resulting shared library has very few functions that are however enough
to make a full API working, provided you'll follow a few principles. The API
is:

.. function:: void rpython_startup_code(void);

   This is a function that you have to call (once) before calling anything.
   It initializes the RPython/PyPy GC and does a bunch of necessary startup
   code. This function cannot fail.

.. function:: void pypy_init_threads(void);

   Initialize threads. Only need to be called if there are any threads involved
   XXXX double check

.. function:: long pypy_setup_home(char* home, int verbose);

   This is another function that you have to call at some point, without
   it you would not be able to find the standard library (and run pretty much
   nothing). Arguments:

   * ``home``: null terminated path

   * ``verbose``: if non-zero, would print error messages to stderr

   Function returns 0 on success or 1 on failure, can be called multiple times
   until the library is found.

.. function:: int pypy_execute_source(char* source);

   Execute the source code given in the ``source`` argument. Will print
   the error message to stderr upon failure and return 1, otherwise returns 0.
   You should really do your own error handling in the source. It'll acquire
   

.. function:: void pypy_thread_attach(void);

   In case your application uses threads that are initialized outside of PyPy,
   you need to call this function to tell the PyPy GC to track this thread.
   Note that this function is not thread-safe itself, so you need to guard it
   with a mutex.

Simple example
--------------


Threading
---------

XXXX I don't understand what's going on, discuss with unbit

.. _`cffi`: xxx
.. _`uwsgi`: xxx
.. _`PyPy uwsgi plugin`: xxx
