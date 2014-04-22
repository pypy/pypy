======================
Transactional Memory
======================

.. contents::


This page is about ``pypy-stm``, a special in-development version of
PyPy which can run multiple independent CPU-hungry threads in the same
process in parallel.  It is side-stepping what is known in the Python
world as the "global interpreter lock (GIL)" problem.

"STM" stands for Software Transactional Memory, the technique used
internally.  This page describes ``pypy-stm`` from the perspective of a
user, describes work in progress, and finally gives references to more
implementation details.

This work was done mostly by Remi Meier and Armin Rigo.  Thanks to all
donors for crowd-funding the work so far!  Please have a look at the
`2nd call for donation`_.

.. _`2nd call for donation`: http://pypy.org/tmdonate2.html


Introduction
============

``pypy-stm`` is a variant of the regular PyPy interpreter.  With caveats
listed below, it should be in theory within 25%-50% slower than a
regular PyPy, comparing the JIT version in both cases.  It is called
STM for Software Transactional Memory, which is the internal technique
used (see `Reference to implementation details`_).

What you get in exchange for this slow-down is that ``pypy-stm`` runs
any multithreaded Python program on multiple CPUs at once.  Programs
running two threads or more in parallel should ideally run faster than
in a regular PyPy, either now or soon as issues are fixed.  In one way,
that's all there is to it: this is a GIL-less Python, feel free to
`download and try it`__.  However, the deeper idea behind the
``pypy-stm`` project is to improve what is so far the state-of-the-art
for using multiple CPUs, which for cases where separate processes don't
work is done by writing explicitly multi-threaded programs.  Instead,
``pypy-stm`` is pushing forward an approach to *hide* the threads, as
described below in `atomic sections`_.


.. __:

Current status
==============

**pypy-stm requires 64-bit Linux for now.**

Development is done in the branch `stmgc-c7`_.  If you are only
interested in trying it out, you can download a Ubuntu 12.04 binary
here__ (``pypy-2.2.x-stm*.tar.bz2``; this version is a release mode,
but not stripped of debug symbols).  The current version supports four
"segments", which means that it will run up to four threads in parallel,
in other words it is running a thread pool up to 4 threads emulating normal
threads.

To build a version from sources, you first need to compile a custom
version of clang; we recommend downloading `llvm and clang like
described here`__, but at revision 201645 (use ``svn co -r 201645 ...``
for all checkouts).  Then apply all the patches in `this directory`__:
they are fixes for the very extensive usage that pypy-stm does of a
clang-only feature (without them, you get crashes of clang).  Then get
the branch `stmgc-c7`_ of PyPy and run::

   rpython/bin/rpython -Ojit --stm pypy/goal/targetpypystandalone.py

.. _`stmgc-c7`: https://bitbucket.org/pypy/pypy/src/stmgc-c7/
.. __: http://cobra.cs.uni-duesseldorf.de/~buildmaster/misc/
.. __: http://clang.llvm.org/get_started.html
.. __: https://bitbucket.org/pypy/stmgc/src/default/c7/llvmfix/


Caveats:

* So far, small examples work fine, but there are still a number of
  bugs.  We're busy fixing them.

* Currently limited to 1.5 GB of RAM (this is just a parameter in
  `core.h`__).  Memory overflows are not detected correctly, so may
  cause segmentation faults.

* The JIT warm-up time is abysmal (as opposed to the regular PyPy's,
  which is "only" bad).  Moreover, you should run it with a command like
  ``pypy-stm --jit trace_limit=60000 args...``; the default value of
  6000 for ``trace_limit`` is currently too low (6000 should become
  reasonable again as we improve).  Also, in order to produce machine
  code, the JIT needs to enter a special single-threaded mode for now.
  This all means that you *will* get very bad performance results if
  your program doesn't run for *many* seconds for now.

* The GC is new; although clearly inspired by PyPy's regular GC, it
  misses a number of optimizations for now.  Programs allocating large
  numbers of small objects that don't immediately die, as well as
  programs that modify large lists or dicts, suffer from these missing
  optimizations.

* The GC has no support for destructors: the ``__del__`` method is never
  called (including on file objects, which won't be closed for you).
  This is of course temporary.  Also, weakrefs might appear to work a
  bit strangely for now (staying alive even though ``gc.collect()``, or
  even dying but then un-dying for a short time before dying again).

* The STM system is based on very efficient read/write barriers, which
  are mostly done (their placement could be improved a bit in
  JIT-generated machine code).  But the overall bookkeeping logic could
  see more improvements (see Statistics_ below).

* You can use `atomic sections`_, but the most visible missing thing is
  that you don't get reports about the "conflicts" you get.  This would
  be the first thing that you need in order to start using atomic
  sections more extensively.  Also, for now: for better results, try to
  explicitly force a transaction break just before (and possibly after)
  each large atomic section, with ``time.sleep(0)``.

* Forking the process is slow because the complete memory needs to be
  copied manually right now.

* Very long-running processes should eventually crash on an assertion
  error because of a non-implemented overflow of an internal 29-bit
  number, but this requires at the very least ten hours --- more
  probably, several days or more.

.. _`report bugs`: https://bugs.pypy.org/
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/src_stm/stm/core.h



Statistics
==========

When a non-main thread finishes, you get statistics printed to stderr,
looking like that::

      thread 0x7f73377fe600:
          outside transaction          42182  0.506 s
          run current                  85466  0.000 s
          run committed                34262  3.178 s
          run aborted write write       6982  0.083 s
          run aborted write read         550  0.005 s
          run aborted inevitable         388  0.010 s
          run aborted other                0  0.000 s
          wait free segment                0  0.000 s
          wait write read                 78  0.027 s
          wait inevitable                887  0.490 s
          wait other                       0  0.000 s
          bookkeeping                  51418  0.606 s
          minor gc                    162970  1.135 s
          major gc                         1  0.019 s
          sync pause                   59173  1.738 s
          spin loop                   129512  0.094 s

The first number is a counter; the second number gives the associated
time (the amount of real time that the thread was in this state; the sum
of all the times should be equal to the total time between the thread's
start and the thread's end).  The most important points are "run
committed", which gives the amount of useful work, and "outside
transaction", which should give the time spent e.g. in library calls
(right now it seems to be a bit larger than that; to investigate).
Everything else is overhead of various forms.  (Short-, medium- and
long-term future work involves reducing this overhead :-)

These statistics are not printed out for the main thread, for now.


Atomic sections
===============

While one of the goal of pypy-stm is to give a GIL-free but otherwise
unmodified Python, the other goal is to push for a better way to use
multithreading.  For this, you (as the Python programmer) get an API
in the ``__pypy__.thread`` submodule:

* ``__pypy__.thread.atomic``: a context manager (i.e. you use it in
  a ``with __pypy__.thread.atomic:`` statement).  It runs the whole
  block of code without breaking the current transaction --- from
  the point of view of a regular CPython/PyPy, this is equivalent to
  saying that the GIL will not be released at all between the start and
  the end of this block of code.

The obvious usage is to use atomic blocks in the same way as one would
use locks: to protect changes to some shared data, you do them in a
``with atomic`` block, just like you would otherwise do them in a ``with
mylock`` block after ``mylock = thread.allocate_lock()``.  This allows
you not to care about acquiring the correct locks in the correct order;
it is equivalent to having only one global lock.  This is how
transactional memory is `generally described`__: as a way to efficiently
execute such atomic blocks, running them in parallel while giving the
illusion that they run in some serial order.

.. __: http://en.wikipedia.org/wiki/Transactional_memory

However, the less obvious intended usage of atomic sections is as a
wide-ranging replacement of explicit threads.  You can turn a program
that is not multi-threaded at all into a program that uses threads
internally, together with large atomic sections to keep the behavior
unchanged.  This capability can be hidden in a library or in the
framework you use; the end user's code does not need to be explicitly
aware of using threads.  For a simple example of this, see
`transaction.py`_ in ``lib_pypy``.  The idea is that if you have a
program where the function ``f(key, value)`` runs on every item of some
big dictionary, you can replace the loop with::

    for key, value in bigdict.items():
        transaction.add(f, key, value)
    transaction.run()

This code runs the various calls to ``f(key, value)`` using a thread
pool, but every single call is done in an atomic section.  The end
result is that the behavior should be exactly equivalent: you don't get
any extra multithreading issue.

This approach hides the notion of threads from the end programmer,
including all the hard multithreading-related issues.  This is not the
first alternative approach to explicit threads; for example, OpenMP_ is
one.  However, it is one of the first ones which does not require the
code to be organized in a particular fashion.  Instead, it works on any
Python program which has got latent, imperfect parallelism.  Ideally, it
only requires that the end programmer identifies where this parallelism
is likely to be found, and communicates it to the system, using for
example the ``transaction.add()`` scheme.

.. _`transaction.py`: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/lib_pypy/transaction.py
.. _OpenMP: http://en.wikipedia.org/wiki/OpenMP

==================

Other APIs in pypy-stm:

* ``__pypy__.thread.getsegmentlimit()``: return the number of "segments"
  in this pypy-stm.  This is the limit above which more threads will not
  be able to execute on more cores.  (Right now it is limited to 4 due
  to inter-segment overhead, but should be increased in the future.  It
  should also be settable, and the default value should depend on the
  number of actual CPUs.)

* ``__pypy__.thread.exclusive_atomic``: same as ``atomic``, but
  raises an exception if you attempt to nest it inside another
  ``atomic``.

* ``__pypy__.thread.signals_enabled``: a context manager that runs
  its block with signals enabled.  By default, signals are only
  enabled in the main thread; a non-main thread will not receive
  signals (this is like CPython).  Enabling signals in non-main threads
  is useful for libraries where threads are hidden and the end user is
  not expecting his code to run elsewhere than in the main thread.

Note that all of this API is (or will be) implemented in a regular PyPy
too: for example, ``with atomic`` will simply mean "don't release the
GIL" and ``getsegmentlimit()`` will return 1.

==================


Reference to implementation details
===================================

The core of the implementation is in a separate C library called stmgc_,
in the c7_ subdirectory.  Please see the `README.txt`_ for more
information.  In particular, the notion of segment is discussed there.

.. _stmgc: https://bitbucket.org/pypy/stmgc/src/default/
.. _c7: https://bitbucket.org/pypy/stmgc/src/default/c7/
.. _`README.txt`: https://bitbucket.org/pypy/stmgc/raw/default/c7/README.txt

PyPy itself adds on top of it the automatic placement of read__ and write__
barriers and of `"becomes-inevitable-now" barriers`__, the logic to
`start/stop transactions as an RPython transformation`__ and as
`supporting`__ `C code`__, and the support in the JIT (mostly as a
`transformation step on the trace`__ and generation of custom assembler
in `assembler.py`__).

.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/readbarrier.py
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/memory/gctransform/stmframework.py
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/inevitable.py
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/jitdriver.py
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/src_stm/stmgcintf.h
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/src_stm/stmgcintf.c
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/jit/backend/llsupport/stmrewrite.py
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/jit/backend/x86/assembler.py
