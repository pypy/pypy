
Embedding PyPy
--------------

PyPy has a very minimal and a very strange embedding interface, based on
the usage of `cffi`_ and the philosophy that Python is a better language than
C. It was developed in collaboration with Roberto De Ioris from the `uwsgi`_
project. The `PyPy uwsgi plugin`_ is a good example of using the embedding API.

The first thing that you need is to compile PyPy yourself with the option
``--shared``. We plan to make ``--shared`` the default in the future. Consult
the `how to compile PyPy`_ doc for details. This will result in ``libpypy.so``
or ``pypy.dll`` file or something similar, depending on your platform. Consult
your platform specification for details.

The resulting shared library exports very few functions, however they are
enough to accomplish everything you need, provided you follow a few principles.
The API is:

.. function:: void rpython_startup_code(void);

   This is a function that you have to call (once) before calling anything else.
   It initializes the RPython/PyPy GC and does a bunch of necessary startup
   code. This function cannot fail.

.. function:: void pypy_init_threads(void);

   Initialize threads. Only need to be called if there are any threads involved

.. function:: long pypy_setup_home(char* home, int verbose);

   This function searches the PyPy standard library starting from the given
   "PyPy home directory".  It is not strictly necessary to execute it before
   running Python code, but without it you will not be able to import any
   non-builtin module from the standard library.  The arguments are:

   * ``home``: NULL terminated path to an executable inside the pypy directory
     (can be a .so name, can be made up)

   * ``verbose``: if non-zero, it will print error messages to stderr

   Function returns 0 on success or -1 on failure, can be called multiple times
   until the library is found.

.. function:: int pypy_execute_source(char* source);

   Execute the Python source code given in the ``source`` argument. In case of
   exceptions, it will print the Python traceback to stderr and return 1,
   otherwise return 0.  You should really do your own error handling in the
   source. It'll acquire the GIL.

.. function:: int pypy_execute_source_ptr(char* source, void* ptr);

   Just like the above, except it registers a magic argument in the source
   scope as ``c_argument``, where ``void*`` is encoded as Python int.

.. function:: void pypy_thread_attach(void);

   In case your application uses threads that are initialized outside of PyPy,
   you need to call this function to tell the PyPy GC to track this thread.
   Note that this function is not thread-safe itself, so you need to guard it
   with a mutex.

Simple example
--------------

Note that this API is a lot more minimal than say CPython C API, so at first
it's obvious to think that you can't do much. However, the trick is to do
all the logic in Python and expose it via `cffi`_ callbacks. Let's assume
we're on linux and pypy is installed in ``/opt/pypy`` with the
library in ``/opt/pypy/bin/libpypy-c.so``.  (It doesn't need to be
installed; you can also replace this path with your local checkout.)
We write a little C program:

.. code-block:: c

    #include "include/PyPy.h"
    #include <stdio.h>

    const char source[] = "print 'hello from pypy'";

    int main()
    {
      int res;

      rpython_startup_code();
      // pypy_setup_home() is not needed in this trivial example
      res = pypy_execute_source((char*)source);
      if (res) {
        printf("Error calling pypy_execute_source!\n");
      }
      return res;
    }

If we save it as ``x.c`` now, compile it and run it with::

    fijal@hermann:/opt/pypy$ gcc -o x x.c -lpypy-c -L.
    fijal@hermann:/opt/pypy$ LD_LIBRARY_PATH=. ./x
    hello from pypy

Worked!

More advanced example
---------------------

Typically we need something more to do than simply execute source. The following
is a fully fledged example, please consult cffi documentation for details.
It's a bit longish, but it captures a gist what can be done with the PyPy
embedding interface:

.. code-block:: c

    #include "include/PyPy.h"
    #include <stdio.h>

    char source[] = "from cffi import FFI\n\
    ffi = FFI()\n\
    @ffi.callback('int(int)')\n\
    def func(a):\n\
        print 'Got from C %d' % a\n\
        return a * 2\n\
    ffi.cdef('int callback(int (*func)(int));')\n\
    c_func = ffi.cast('int(*)(int(*)(int))', c_argument)\n\
    c_func(func)\n\
    print 'finished the Python part'\n\
    ";

    int callback(int (*func)(int))
    {
        printf("Calling to Python, result: %d\n", func(3));
    }

    int main()
    {
        int res;
        void *lib, *func;

        rpython_startup_code();
        res = pypy_setup_home("/opt/pypy/bin/libpypy-c.so", 1);
        if (res) {
            printf("Error setting pypy home!\n");
            return 1;
        }
        res = pypy_execute_source_ptr(source, (void*)callback);
        if (res) {
            printf("Error calling pypy_execute_source_ptr!\n");
        }
        return res;
    }

you can compile and run it with::

   fijal@hermann:/opt/pypy$ gcc -g -o x x.c -lpypy-c -L.
   fijal@hermann:/opt/pypy$ LD_LIBRARY_PATH=. ./x
   Got from C 3
   Calling to Python, result: 6
   finished the Python part

As you can see, we successfully managed to call Python from C and C from
Python. Now having one callback might not be enough, so what typically happens
is that we would pass a struct full of callbacks to ``pypy_execute_source_ptr``
and fill the structure from Python side for the future use.

Threading
---------

In case you want to use pthreads, what you need to do is to call
``pypy_thread_attach`` from each of the threads that you created (but not
from the main thread) and call ``pypy_init_threads`` from the main thread.

.. _`cffi`: http://cffi.readthedocs.org/
.. _`uwsgi`: http://uwsgi-docs.readthedocs.org/en/latest/
.. _`PyPy uwsgi plugin`: http://uwsgi-docs.readthedocs.org/en/latest/PyPy.html
.. _`how to compile PyPy`: getting-started.html
