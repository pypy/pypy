
=============================
Software Transactional Memory
=============================

.. contents::


This page is about ``pypy-stm``, a special in-development version of
PyPy which can run multiple independent CPU-hungry threads in the same
process in parallel.  It is a solution to what is known in the Python
world as the "global interpreter lock (GIL)" problem --- it is an
implementation of Python without the GIL.

"STM" stands for Software `Transactional Memory`_, the technique used
internally.  This page describes ``pypy-stm`` from the perspective of a
user, describes work in progress, and finally gives references to more
implementation details.

This work was done by Remi Meier and Armin Rigo.  Thanks to all donors
for crowd-funding the work so far!  Please have a look at the `2nd call
for donation`_.

.. _`Transactional Memory`: http://en.wikipedia.org/wiki/Transactional_memory
.. _`2nd call for donation`: http://pypy.org/tmdonate2.html


Introduction
============

``pypy-stm`` is a variant of the regular PyPy interpreter.  (This
version supports Python 2.7; see below for `Python 3`_.)  With caveats_
listed below, it should be in theory within 20%-50% slower than a
regular PyPy, comparing the JIT version in both cases (but see below!).
It is called
STM for Software Transactional Memory, which is the internal technique
used (see `Reference to implementation details`_).

The benefit is that the resulting ``pypy-stm`` can execute multiple
threads of Python code in parallel.  Programs running two threads or
more in parallel should ideally run faster than in a regular PyPy
(either now, or soon as bugs are fixed).

* ``pypy-stm`` is fully compatible with a GIL-based PyPy; you can use
  it as a drop-in replacement and multithreaded programs will run on
  multiple cores.

* ``pypy-stm`` does not impose any special API to the user, but it
  provides a new pure Python module called `transactional_memory`_ with
  features to inspect the state or debug conflicts_ that prevent
  parallelization.  This module can also be imported on top of a non-STM
  PyPy or CPython.

* Building on top of the way the GIL is removed, we will talk
  about `Atomic sections, Transactions, etc.: a better way to write
  parallel programs`_.


Getting Started
===============

**pypy-stm requires 64-bit Linux for now.**

Development is done in the branch `stmgc-c7`_.  If you are only
interested in trying it out, you can download a Ubuntu binary here__
(``pypy-stm-2.3*.tar.bz2``, Ubuntu 12.04-14.04).  The current version
supports four "segments", which means that it will run up to four
threads in parallel.

To build a version from sources, you first need to compile a custom
version of clang(!); we recommend downloading `llvm and clang like
described here`__, but at revision 201645 (use ``svn co -r 201645 <path>``
for all checkouts).  Then apply all the patches in `this directory`__:
they are fixes for a clang-only feature that hasn't been used so heavily
in the past (without the patches, you get crashes of clang).  Then get
the branch `stmgc-c7`_ of PyPy and run::

   rpython/bin/rpython -Ojit --stm pypy/goal/targetpypystandalone.py

.. _`stmgc-c7`: https://bitbucket.org/pypy/pypy/src/stmgc-c7/
.. __: https://bitbucket.org/pypy/pypy/downloads/
.. __: http://clang.llvm.org/get_started.html
.. __: https://bitbucket.org/pypy/stmgc/src/default/c7/llvmfix/


.. _caveats:

Current status
--------------

* So far, small examples work fine, but there are still a few bugs.
  We're busy fixing them as we find them; feel free to `report bugs`_.

* It runs with an overhead as low as 20% on examples like "richards".
  There are also other examples with higher overheads --currently up to
  2x for "translate.py"-- which we are still trying to understand.
  One suspect is our partial GC implementation, see below.

* Currently limited to 1.5 GB of RAM (this is just a parameter in
  `core.h`__).  Memory overflows are not correctly handled; they cause
  segfaults.

* The JIT warm-up time improved recently but is still bad.  In order to
  produce machine code, the JIT needs to enter a special single-threaded
  mode for now.  This means that you will get bad performance results if
  your program doesn't run for several seconds, where *several* can mean
  *many.*  When trying benchmarks, be sure to check that you have
  reached the warmed state, i.e. the performance is not improving any
  more.  This should be clear from the fact that as long as it's
  producing more machine code, ``pypy-stm`` will run on a single core.

* The GC is new; although clearly inspired by PyPy's regular GC, it
  misses a number of optimizations for now.  Programs allocating large
  numbers of small objects that don't immediately die (surely a common
  situation) suffer from these missing optimizations.

* The GC has no support for destructors: the ``__del__`` method is never
  called (including on file objects, which won't be closed for you).
  This is of course temporary.  Also, weakrefs might appear to work a
  bit strangely for now (staying alive even though ``gc.collect()``, or
  even dying but then un-dying for a short time before dying again).

* The STM system is based on very efficient read/write barriers, which
  are mostly done (their placement could be improved a bit in
  JIT-generated machine code).  But the overall bookkeeping logic could
  see more improvements (see `Low-level statistics`_ below).

* Forking the process is slow because the complete memory needs to be
  copied manually.  A warning is printed to this effect.

* Very long-running processes (on the order of days) will eventually
  crash on an assertion error because of a non-implemented overflow of
  an internal 29-bit number.

.. _`report bugs`: https://bugs.pypy.org/
.. __: https://bitbucket.org/pypy/pypy/raw/stmgc-c7/rpython/translator/stm/src_stm/stm/core.h



Python 3
========

In this document I describe "pypy-stm", which is based on PyPy's Python
2.7 interpreter.  Supporting Python 3 should take about half an
afternoon of work.  Obviously, what I *don't* mean is that by tomorrow
you can have a finished and polished "pypy3-stm" product.  General py3k
work is still missing; and general stm work is also still missing.  But
they are rather independent from each other, as usual in PyPy.  The
required afternoon of work will certainly be done one of these days now
that the internal interfaces seem to stabilize.

The same is true for other languages implemented in the RPython
framework, although the amount of work to put there might vary, because
the STM framework within RPython is currently targeting the PyPy
interpreter and other ones might have slightly different needs.



User Guide
==========

Drop-in replacement
-------------------

Multithreaded, CPU-intensive Python programs should work unchanged on
``pypy-stm``.  They will run using multiple CPU cores in parallel.

The existing semantics of the GIL (Global Interpreter Lock) are
unchanged: although running on multiple cores in parallel, ``pypy-stm``
gives the illusion that threads are run serially, with switches only
occurring between bytecodes, not in the middle of them.  Programs can
rely on this: using ``shared_list.append()/pop()`` or
``shared_dict.setdefault()`` as synchronization mecanisms continues to
work as expected.

This works by internally considering the points where a standard PyPy or
CPython would release the GIL, and replacing them with the boundaries of
"transaction".  Like their database equivalent, multiple transactions
can execute in parallel, but will commit in some serial order.  They
appear to behave as if they were completely run in this serialization
order.


Atomic sections
---------------

PyPy supports *atomic sections,* which are blocks of code which you want
to execute without "releasing the GIL".  *This is experimental and may
be removed in the future.*  In STM terms, this means blocks of code that
are executed while guaranteeing that the transaction is not interrupted
in the middle.

Here is a usage example::

    with __pypy__.thread.atomic:
        assert len(lst1) == 10
        x = lst1.pop(0)
        lst1.append(x)

In this (bad) example, we are sure that the item popped off one end of
the list is appened again at the other end atomically.  It means that
another thread can run ``len(lst1)`` or ``x in lst1`` without any
particular synchronization, and always see the same results,
respectively ``10`` and ``True``.  It will never see the intermediate
state where ``lst1`` only contains 9 elements.  Atomic sections are
similar to re-entrant locks (they can be nested), but additionally they
protect against the concurrent execution of *any* code instead of just
code that happens to be protected by the same lock in other threads.

Note that the notion of atomic sections is very strong. If you write
code like this::

    with __pypy__.thread.atomic:
        time.sleep(10)

then, if you think about it as if we had a GIL, you are executing a
10-seconds-long atomic transaction without releasing the GIL at all.
This prevents all other threads from progressing at all.  While it is
not strictly true in ``pypy-stm``, the exact rules for when other
threads can progress or not are rather complicated; you have to consider
it likely that such a piece of code will eventually block all other
threads anyway.

Note that if you want to experiment with ``atomic``, you may have to add
manually a transaction break just before the atomic block.  This is
because the boundaries of the block are not guaranteed to be the
boundaries of the transaction: the latter is at least as big as the
block, but maybe bigger.  Therefore, if you run a big atomic block, it
is a good idea to break the transaction just before.  This can be done
e.g. by the hack of calling ``time.sleep(0)``.  (This may be fixed at
some point.)

There are also issues with the interaction of locks and atomic blocks.
This can be seen if you write to files (which have locks), including
with a ``print`` to standard output.  If one thread tries to acquire a
lock while running in an atomic block, and another thread has got the
same lock, then the former may fail with a ``thread.error``.  The reason
is that "waiting" for some condition to become true --while running in
an atomic block-- does not really make sense.  For now you can work
around it by making sure that, say, all your prints are either in an
``atomic`` block or none of them are.  (This kind of issue is
theoretically hard to solve.)


Locks
-----

**Not Implemented Yet**

The thread module's locks have their basic semantic unchanged.  However,
using them (e.g. in ``with my_lock:`` blocks) starts an alternative
running mode, called `Software lock elision`_.  This means that PyPy
will try to make sure that the transaction extends until the point where
the lock is released, and if it succeeds, then the acquiring and
releasing of the lock will be "elided".  This means that in this case,
the whole transaction will technically not cause any write into the lock
object --- it was unacquired before, and is still unacquired after the
transaction.

This is specially useful if two threads run ``with my_lock:`` blocks
with the same lock.  If they each run a transaction that is long enough
to contain the whole block, then all writes into the lock will be elided
and the two transactions will not conflict with each other.  As usual,
they will be serialized in some order: one of the two will appear to run
before the other.  Simply, each of them executes an "acquire" followed
by a "release" in the same transaction.  As explained above, the lock
state goes from "unacquired" to "unacquired" and can thus be left
unchanged.

This approach can gracefully fail: unlike atomic sections, there is no
guarantee that the transaction runs until the end of the block.  If you
perform any input/output while you hold the lock, the transaction will
end as usual just before the input/output operation.  If this occurs,
then the lock elision mode is cancelled and the lock's "acquired" state
is really written.

Even if the lock is really acquired already, a transaction doesn't have
to wait for it to become free again.  It can enter the elision-mode anyway
and tentatively execute the content of the block.  It is only at the end,
when trying to commit, that the thread will pause.  As soon as the real
value stored in the lock is switched back to "unacquired", it can then
proceed and attempt to commit its already-executed transaction (which
can fail and abort and restart from the scratch, as usual).

Note that this is all *not implemented yet,* but we expect it to work
even if you acquire and release several locks.  The elision-mode
transaction will extend until the first lock you acquired is released,
or until the code performs an input/output or a wait operation (for
example, waiting for another lock that is currently not free).  In the
common case of acquiring several locks in nested order, they will all be
elided by the same transaction.

.. _`software lock elision`: https://www.repository.cam.ac.uk/handle/1810/239410


Atomic sections, Transactions, etc.: a better way to write parallel programs
----------------------------------------------------------------------------

(This section is based on locks as we plan to implement them, but also
works with the existing atomic sections.)

In the cases where elision works, the block of code can run in parallel
with other blocks of code *even if they are protected by the same lock.*
You still get the illusion that the blocks are run sequentially.  This
works even for multiple threads that run each a series of such blocks
and nothing else, protected by one single global lock.  This is
basically the Python application-level equivalent of what was done with
the interpreter in ``pypy-stm``: while you think you are writing
thread-unfriendly code because of this global lock, actually the
underlying system is able to make it run on multiple cores anyway.

This capability can be hidden in a library or in the framework you use;
the end user's code does not need to be explicitly aware of using
threads.  For a simple example of this, there is `transaction.py`_ in
``lib_pypy``.  The idea is that you write, or already have, some program
where the function ``f(key, value)`` runs on every item of some big
dictionary, say::

    for key, value in bigdict.items():
        f(key, value)

Then you simply replace the loop with::

    for key, value in bigdict.items():
        transaction.add(f, key, value)
    transaction.run()

This code runs the various calls to ``f(key, value)`` using a thread
pool, but every single call is executed under the protection of a unique
lock.  The end result is that the behavior is exactly equivalent --- in
fact it makes little sense to do it in this way on a non-STM PyPy or on
CPython.  But on ``pypy-stm``, the various locked calls to ``f(key,
value)`` can tentatively be executed in parallel, even if the observable
result is as if they were executed in some serial order.

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


.. _`transactional_memory`:

API of transactional_memory
---------------------------

The new pure Python module ``transactional_memory`` runs on both CPython
and PyPy, both with and without STM.  It contains:

* ``getsegmentlimit()``: return the number of "segments" in
  this pypy-stm.  This is the limit above which more threads will not be
  able to execute on more cores.  (Right now it is limited to 4 due to
  inter-segment overhead, but should be increased in the future.  It
  should also be settable, and the default value should depend on the
  number of actual CPUs.)  If STM is not available, this returns 1.

* ``print_abort_info(minimum_time=0.0)``: debugging help.  Each thread
  remembers the longest abort or pause it did because of cross-thread
  contention_.  This function prints it to ``stderr`` if the time lost
  is greater than ``minimum_time`` seconds.  The record is then
  cleared, to make it ready for new events.  This function returns
  ``True`` if it printed a report, and ``False`` otherwise.


API of __pypy__.thread
----------------------

The ``__pypy__.thread`` submodule is a built-in module of PyPy that
contains a few internal built-in functions used by the
``transactional_memory`` module, plus the following:

* ``__pypy__.thread.atomic``: a context manager to run a block in
  fully atomic mode, without "releasing the GIL".  (May be eventually
  removed?)

* ``__pypy__.thread.signals_enabled``: a context manager that runs its
  block with signals enabled.  By default, signals are only enabled in
  the main thread; a non-main thread will not receive signals (this is
  like CPython).  Enabling signals in non-main threads is useful for
  libraries where threads are hidden and the end user is not expecting
  his code to run elsewhere than in the main thread.


.. _contention:

Conflicts
---------

Based on Software Transactional Memory, the ``pypy-stm`` solution is
prone to "conflicts".  To repeat the basic idea, threads execute their code
speculatively, and at known points (e.g. between bytecodes) they
coordinate with each other to agree on which order their respective
actions should be "committed", i.e. become globally visible.  Each
duration of time between two commit-points is called a transaction.

A conflict occurs when there is no consistent ordering.  The classical
example is if two threads both tried to change the value of the same
global variable.  In that case, only one of them can be allowed to
proceed, and the other one must be either paused or aborted (restarting
the transaction).  If this occurs too often, parallelization fails.

How much actual parallelization a multithreaded program can see is a bit
subtle.  Basically, a program not using ``__pypy__.thread.atomic`` or
eliding locks, or doing so for very short amounts of time, will
parallelize almost freely (as long as it's not some artificial example
where, say, all threads try to increase the same global counter and do
nothing else).

However, using if the program requires longer transactions, it comes
with less obvious rules.  The exact details may vary from version to
version, too, until they are a bit more stabilized.  Here is an
overview.

Parallelization works as long as two principles are respected.  The
first one is that the transactions must not *conflict* with each other.
The most obvious sources of conflicts are threads that all increment a
global shared counter, or that all store the result of their
computations into the same list --- or, more subtly, that all ``pop()``
the work to do from the same list, because that is also a mutation of
the list.  (It is expected that some STM-aware library will eventually
be designed to help with conflict problems, like a STM-aware queue.)

A conflict occurs as follows: when a transaction commits (i.e. finishes
successfully) it may cause other transactions that are still in progress
to abort and retry.  This is a waste of CPU time, but even in the worst
case senario it is not worse than a GIL, because at least one
transaction succeeds (so we get at worst N-1 CPUs doing useless jobs and
1 CPU doing a job that commits successfully).

Conflicts do occur, of course, and it is pointless to try to avoid them
all.  For example they can be abundant during some warm-up phase.  What
is important is to keep them rare enough in total.

Another issue is that of avoiding long-running so-called "inevitable"
transactions ("inevitable" is taken in the sense of "which cannot be
avoided", i.e. transactions which cannot abort any more).  Transactions
like that should only occur if you use ``__pypy__.thread.atomic``,
generally become of I/O in atomic blocks.  They work, but the
transaction is turned inevitable before the I/O is performed.  For all
the remaining execution time of the atomic block, they will impede
parallel work.  The best is to organize the code so that such operations
are done completely outside ``__pypy__.thread.atomic``.

(This is related to the fact that blocking I/O operations are
discouraged with Twisted, and if you really need them, you should do
them on their own separate thread.)

In case of lock elision, we don't get long-running inevitable
transactions, but a different problem can occur: doing I/O cancels lock
elision, and the lock turns into a real lock, preventing other threads
from committing if they also need this lock.  (More about it when lock
elision is implemented and tested.)



Implementation
==============

XXX this section mostly empty for now


Low-level statistics
--------------------

When a non-main thread finishes, you get low-level statistics printed to
stderr, looking like that::

      thread 0x7f73377fe600:
          outside transaction          42182    0.506 s
          run current                  85466    0.000 s
          run committed                34262    3.178 s
          run aborted write write       6982    0.083 s
          run aborted write read         550    0.005 s
          run aborted inevitable         388    0.010 s
          run aborted other                0    0.000 s
          wait free segment                0    0.000 s
          wait write read                 78    0.027 s
          wait inevitable                887    0.490 s
          wait other                       0    0.000 s
          sync commit soon                 1    0.000 s
          bookkeeping                  51418    0.606 s
          minor gc                    162970    1.135 s
          major gc                         1    0.019 s
          sync pause                   59173    1.738 s
          longest recordered marker          0.000826 s
          "File "x.py", line 5, in f"

On each line, the first number is a counter, and the second number gives
the associated time --- the amount of real time that the thread was in
this state.  The sum of all the times should be equal to the total time
between the thread's start and the thread's end.  The most important
points are "run committed", which gives the amount of useful work, and
"outside transaction", which should give the time spent e.g. in library
calls (right now it seems to be larger than that; to investigate).  The
various "run aborted" and "wait" entries are time lost due to
conflicts_.  Everything else is overhead of various forms.  (Short-,
medium- and long-term future work involves reducing this overhead :-)

The last two lines are special; they are an internal marker read by
``transactional_memory.print_abort_info()``.


Reference to implementation details
-----------------------------------

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



See also
========

See also
https://bitbucket.org/pypy/pypy/raw/default/pypy/doc/project-ideas.rst
(section about STM).
