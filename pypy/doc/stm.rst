
=============================
Software Transactional Memory
=============================


Introduction
============

PyPy can be translated in a special mode based on Software Transactional
Memory (STM).  This mode is not compatible with the JIT so far, and moreover
adds a constant run-time overhead in the range 2x to 5x.  The benefit is
that the resulting ``pypy-stm`` can execute multiple threads of Python code
in parallel.


High-level interface
====================

At the lowest levels, the Global Interpreter Lock (GIL) was just
replaced with STM techniques.  This gives a ``pypy-stm`` that should
behave identically to a regular GIL-enabled PyPy, but run multithreaded
programs in a way that scales with the number of cores.  The details of
the implementation are explained below.

However, what we are pushing for is *not writing multithreaded programs*
at all.  It is possible to use higher-level interfaces.  The basic one
is found in the ``transaction`` module (XXX name to change).  Minimal
example of usage::

    for i in range(10):
        transaction.add(do_stuff, i)
    transaction.run()

This schedules and runs all ten ``do_stuff(i)``.  Each one appears to
run serially, but in random order.  It is also possible to ``add()``
more transactions within each transaction, to schedule additional pieces
of work.  The call to ``run()`` returns when all transactions have
completed.

The module is written in pure Python (XXX not written yet, add url).
See the source code to see how it is based on the `low-level interface`_.


Low-level interface
===================

``pypy-stm`` offers one additional low-level API: ``thread.atomic``.
This is a context manager to use in a ``with`` statement.  Any code
running in the ``with thread.atomic`` block is guaranteed to be fully
serialized with respect to any code run by other threads (so-called
*strong isolation*).

Note that this is a guarantee of observed behavior: under the conditions
described below, multiple ``thread.atomic`` blocks can actually run in
parallel.

Classical minimal example: in a thread, you want to pop an item from
``list1`` and append it to ``list2``, knowing that both lists can be
mutated concurrently by other threads.  Using ``thread.atomic`` this
can be done without careful usage of locks::

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
        print "hello, the value is:"
        print "\t", value

actually also helps ensuring that the whole line or lines are printed
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
multithreaded program works as if all transactions were serialized, but
actually executing the transactions in parallel.

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

Every transaction can further be in one of two modes: either "normal" or
"inevitable".  To simplify, a transaction starts in "normal" mode, but
switches to "inevitable" as soon as it performs input/output.  If we
have an inevitable transaction, all other transactions are paused; this
effect is similar to the GIL.

In the absence of ``thread.atomic``, inevitable transactions only have a
small effect.  Indeed, as soon as the current bytecode finishes, the
interpreter notices that the transaction is inevitable and immediately
introduces a transaction break in order to switch back to a normal-mode
transaction.  It means that inevitable transactions only run for a short
fraction of the time.

With ``thread.atomic`` however you have to be a bit careful, because the
next transaction break will only occur after the end of the outermost
``with thread.atomic``.  Basically, you should organize your code in
such a way that for any ``thread.atomic`` block that runs for a
noticable time, any I/O is done near the end of it, not when there is
still a lot of CPU time ahead.


Implementation
==============

XXX
