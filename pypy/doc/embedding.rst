
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

.. function:: char* rpython_startup_code(void);

   This is a function that you have to call (once) before calling anything.
   It initializes the RPython/PyPy GC and does a bunch of necessary startup
   code. This function cannot fail and always returns NULL.

.. function:: void pypy_init_threads(void);

   Initialize threads. Only need to be called if there are any threads involved

.. function:: long pypy_setup_home(char* home, int verbose);

   This is another function that you have to call at some point, without
   it you would not be able to find the standard library (and run pretty much
   nothing). Arguments:

   * ``home``: null terminated path to an executable inside the pypy directory
     (can be a .so name, can be made up)

   * ``verbose``: if non-zero, would print error messages to stderr

   Function returns 0 on success or 1 on failure, can be called multiple times
   until the library is found.

.. function:: int pypy_execute_source(char* source);

   Execute the source code given in the ``source`` argument. Will print
   the error message to stderr upon failure and return 1, otherwise returns 0.
   You should really do your own error handling in the source. It'll acquire
   the GIL.

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
we're on linux and pypy is put in ``/opt/pypy`` (a source checkout) and
library is in ``/opt/pypy/libpypy-c.so``. We write a little C program
(for simplicity assuming that all operations will be performed::

  #include "include/PyPy.h"
  #include <stdio.h>

  const char source[] = "print 'hello from pypy'";

  int main()
  {
    int res;

    rpython_startup_code();
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
embedding interface::

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
            res = pypy_setup_home("/opt/pypy/pypy/libpypy-c.so", 1);
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



Threading
---------

XXXX I don't understand what's going on, discuss with unbit

.. _`cffi`: http://cffi.readthedocs.org/
.. _`uwsgi`: http://uwsgi-docs.readthedocs.org/en/latest/
.. _`PyPy uwsgi plugin`: http://uwsgi-docs.readthedocs.org/en/latest/PyPy.html
