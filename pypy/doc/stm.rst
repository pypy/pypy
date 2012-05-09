
=============================
Software Transactional Memory
=============================


Introduction
============

PyPy can be translated in a special mode based on Software Transactional
Memory (STM).  This mode is not compatible with the JIT so far, and moreover
adds a constant run-time overhead, expected to be in the range 2x to 5x.
(XXX for now it is bigger, but past experience show it can be reduced.)
The benefit is that the resulting ``pypy-stm`` can execute multiple
threads of Python code in parallel.

* ``pypy-stm`` is fully compatible with a GIL-based PyPy; you can use it
  as a drop-in replacement and multithreaded programs will run on multiple
  cores.

* ``pypy-stm`` adds a low-level API in the ``thread`` module, namely
  ``thread.atomic``, that can be used as described below.  This is meant
  to improve existing multithread-based programs.  It is also meant to
  be used to build higher-level interfaces on top of it.

* A number of higher-level interfaces are planned, using internally
  threads and ``thread.atomic``.  They are meant to be used in
  non-thread-based programs.  Given the higher level, we also recommend
  using them in new programs instead of structuring your program to use
  raw threads.


High-level interface
====================

The basic high-level interface is planned in the ``transaction`` module
(XXX name can change).  A minimal example of usage will be along the
lines of::

    for i in range(10):
        transaction.add(do_stuff, i)
    transaction.run()

This schedules and runs all ten ``do_stuff(i)``.  Each one appears to
run serially, but in random order.  It is also possible to ``add()``
more transactions within each transaction, causing additional pieces of
work to be scheduled.  The call to ``run()`` returns when all
transactions have completed.

The module is written in pure Python (XXX not written yet, add url).
See the source code to see how it is based on the `low-level interface`_.


Low-level interface
===================

Besides replacing the GIL with STM techniques, ``pypy-stm`` offers one
additional explicit low-level API: ``thread.atomic``.  This is a context
manager to use in a ``with`` statement.  Any code running in the ``with
thread.atomic`` block is guaranteed to be fully serialized with respect
to any code run by other threads (so-called *strong isolation*).

Note that this is a guarantee of observed behavior: under the conditions
described below, a ``thread.atomic`` block can actually run in parallel
with other threads, whether they are in a ``thread.atomic`` or not.

Classical minimal example: in a thread, you want to pop an item from
``list1`` and append it to ``list2``, knowing that both lists can be
mutated concurrently by other threads.  Using ``thread.atomic`` this can
be done without careful usage of locks on any mutation of the lists::

    with thread.atomic:
        x = list1.pop()
        list2.append(x)

Note that, unlike this minimal example, the expected usage is that
``thread.atomic`` blocks are potentially very complex and long-running.
This is what you typically get with the `high-level interface`_.


Interaction with locks
======================

Existing multi-threaded programs usually rely on locks, either directly
from ``thread.allocate_lock()`` or by using variants from the
``threading`` module.  Actually, some operations in the interpreter
itself acquire locks internally too; most notably, any file access does.

These locks work fine in ``pypy-stm`` either outside ``thread.atomic``
blocks or inside ``thread.atomic`` blocks.  However, due to hard
technical issues, it is not really possible for them to work correctly
if a ``thread.atomic`` block tries to acquire a lock that is already
acquired.  In that situation (only), acquiring the lock will raise
``thread.error``.

A common way for this issue to show up is using ``print`` statements,
because of the internal lock on ``stdout``.  You are free to use
``print`` either outside ``thread.atomic`` blocks or inside them, but
not both concurrently.  An easy fix is to put all ``print`` statements
inside ``thread.atomic`` blocks.  Writing this kind of code::

    with thread.atomic:
        print "hello, the value is:", value

actually also helps ensuring that the whole line (or lines) is printed
atomically, instead of being broken up with interleaved output from
other threads.

In this case, it is always a good idea to protect ``print`` statements
by ``thread.atomic``.  But not all file operations benefit: if you have
a read from a file that may block for some time, putting it in a
``thread.atomic`` would have the negative effect of suspending all other
threads while we wait for data to arrive, as described next__.

.. __: Parallelization_


Parallelization
===============

How much actual parallelization a multithreaded program can see is a bit
subtle.  The exact rules may vary over time, too.  Here is an overview.

Each thread is actually running as a sequence of "transactions", which
are separated by "transaction breaks".  The execution of the whole
multithreaded program works as if all transactions were serialized.
You don't see the transactions actually running in parallel.

This works as long as two principles are respected.  The first one is
that the transactions must not *conflict* with each other.  The most
obvious sources of conflicts are threads that all increment a global
shared counter, or that all store the result of their computations into
the same shared list.  (It is expected that some STM-aware library will
eventually be designed to help with sharing problems, like a STM-aware
list or queue.)

The other principle is that of avoiding long-running "inevitable"
transactions.  This is more subtle to understand.  The first thing we
need to learn is where transaction breaks are.  There are two modes of
execution: either we are in a ``with thread.atomic`` block (or possibly
several nested ones), or not.

If we are not in ``thread.atomic`` mode, then transaction breaks occur
at the following places:

* from time to time between the execution of two bytecodes;
* across an external system call.

Transaction breaks *never* occur in ``thread.atomic`` mode.

Additionally, every transaction can further be in one of two modes:
either "normal" or "inevitable".  To simplify, a transaction starts in
"normal" mode, but switches to "inevitable" as soon as it performs
input/output.  If we have an inevitable transaction, all other
transactions are paused; this effect is similar to the GIL.

In the absence of ``thread.atomic``, inevitable transactions only have a
small effect.  Indeed, as soon as the current bytecode finishes, the
interpreter notices that the transaction is inevitable and immediately
introduces a transaction break in order to switch back to a normal-mode
transaction.  It means that inevitable transactions only run for a small
fraction of the time.

With ``thread.atomic`` however you have to be a bit careful, because the
next transaction break will only occur after the end of the outermost
``with thread.atomic``.  Basically, you should organize your code in
such a way that for any ``thread.atomic`` block that runs for a
noticable time, any I/O is done near the end of it, not when there is
still a lot of CPU (or I/O) time ahead.

In particular, this means that you should ideally avoid blocking I/O
operations in ``thread.atomic`` blocks.  They work, but because the
transaction is turned inevitable *before* the I/O is performed, they
will prevent any parallel work at all.  (This may look like
``thread.atomic`` blocks reverse the usual effects of the GIL: if the
block is computation-intensive it will nicely be parallelized, but doing
any long I/O prevents any parallel work.)


Implementation
==============

XXX
