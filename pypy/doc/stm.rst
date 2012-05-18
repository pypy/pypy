
=============================
Software Transactional Memory
=============================


Introduction
============

PyPy can be translated in a special mode based on Software Transactional
Memory (STM).  This mode is not compatible with the JIT so far, and moreover
adds a constant run-time overhead, expected to be in the range 2x to 5x.
(XXX for now it is bigger, but past experience shows it can be reduced.)
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
transactions have completed.  If a transaction raises, the exception
propagates outside the call to ``run()`` and the remaining transactions
are lost (they are not executed, or aborted if they are already in
progress).

The module is written in pure Python (`lib_pypy/transaction.py`_).
See the source code to see how it is based on the `low-level interface`_.


Low-level interface
===================

Besides replacing the GIL with STM techniques, ``pypy-stm`` offers one
additional explicit low-level API: ``thread.atomic``.  This is a context
manager to use in a ``with`` statement.  Any code running in the ``with
thread.atomic`` block is guaranteed to be fully serialized with respect
to any code run by other threads (so-called *strong isolation*).

Note that this is a *guarantee of observed behavior:* under the conditions
described below, a ``thread.atomic`` block can internally run in parallel
with other threads, whether they are in a ``thread.atomic`` or not.  But
the behavior is as if the threads don't overlap.

Classical minimal example: in a thread, you want to pop an item from
``list1`` and append it to ``list2``, knowing that both lists can be
mutated concurrently by other threads.  Using ``thread.atomic`` this can
be done without careful usage of locks on all the mutations of the lists::

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
if a ``thread.atomic`` block tries to acquire a lock that has already
been acquired outside.  In that situation (only), trying to acquire the
lock will raise ``thread.error``.

A common way for this issue to show up is using ``print`` statements,
because of the internal lock on ``stdout``.  You are free to use
``print`` either outside ``thread.atomic`` blocks or inside them, but
not both concurrently.  An easy fix is to put all ``print`` statements
inside ``thread.atomic`` blocks, by writing this kind of code::

    with thread.atomic:
        print "hello, the value is:", value

Note that this actually also helps ensuring that the whole line (or
lines) is printed atomically, instead of being broken up with
interleaved output from other threads.

In this case, it is always a good idea to protect ``print`` statements
with ``thread.atomic``.  The reason it is not done automatically is that
not all file operations would benefit: if you have a read or write that
may block, putting it in a ``thread.atomic`` would have the negative
effect of suspending all other threads while we wait for the call to
complete, as described next__.

.. __: Parallelization_


Parallelization
===============

How much actual parallelization a multithreaded program can see is a bit
subtle.  Basically, a program not using ``thread.atomic`` or using it
for very short amounts of time will parallelize almost freely.  However,
using ``thread.atomic`` for longer periods of time comes with less
obvious rules.  The exact details may vary from version to version, too,
until they are a bit more stabilized.  Here is an overview.

Each thread is actually running as a sequence of "transactions", which
are separated by "transaction breaks".  The execution of the whole
multithreaded program works as if all transactions were serialized.  The
transactions are actually running in parallel, but this is invisible.

This parallelization works as long as two principles are respected.  The
first one is that the transactions must not *conflict* with each other.
The most obvious sources of conflicts are threads that all increment a
global shared counter, or that all store the result of their
computations into the same list --- or, more subtly, that all ``pop()``
the work to do from the same list, because that is also a mutation of
the list.  (It is expected that some STM-aware library will eventually
be designed to help with sharing problems, like a STM-aware list or
queue.)

A conflict occurs as follows: when a transaction commits (i.e. finishes
successfully) it may cause other transactions that are still in progress
to abort and retry.  This is a waste of CPU time, but even in the worst
case senario it is not worse than a GIL, because at least one
transaction succeeded.  Conflicts do occur, of course, and it is
pointless to try to avoid them all.  For example they can be abundant
during some warm-up phase.  What is important is to keep them rare
enough in total.

The other principle is that of avoiding long-running so-called
"inevitable" transactions.  We can consider that a transaction can be in
three possible modes (this is actually a slight simplification):

* *non-atomic:* in this mode, the interpreter is free to insert
  transaction breaks more or less where it wants to.  This is similar to
  how, in CPython, the interpreter is free to release and reacquire the
  GIL where it wants to.  So in non-atomic mode, transaction breaks
  occur from time to time between the execution of two bytecodes, as
  well as across an external system call (the previous transaction is
  committed, the system call is done outside any transaction, and
  finally the next transaction is started).

* *atomic but abortable:* transactions start in this mode at the
  beginning of a ``with thread.atomic`` block.  In atomic mode,
  transaction breaks *never* occur, making a single potentially long
  transaction.  This transaction can be still be aborted if a conflict
  arises, and retried as usual.

* *atomic and inevitable:* as soon as an atomic block does a system
  call, it cannot be aborted any more, because it has visible
  side-effects.  So we turn the transaction "inevitable" --- more
  precisely, this occurs just before doing the system call.  Once the
  system call is started, the transaction cannot be aborted any more:
  it must "inevitably" complete.  This results in the following
  internal restrictions: only one transaction in the whole process can
  be inevitable, and moreover no other transaction can commit before
  the inevitable one --- they will be paused when they reach that point.

So what you should avoid is transactions that are inevitable for a long
period of time.  Doing so blocks essentially all other transactions and
gives an effect similar to the GIL again.  To work around the issue, you
need to organize your code in such a way that for any ``thread.atomic``
block that runs for a noticable amount of time, you perform no I/O at
all before you are close to reaching the end of the block.

Similarly, you should avoid doing any blocking I/O in ``thread.atomic``
blocks.  They work, but because the transaction is turned inevitable
*before* the I/O is performed, they will prevent any parallel work at
all.  You need to organize the code so that such operations are done
completely outside ``thread.atomic``.

(This is related to the fact that blocking I/O operations are
discouraged with Twisted, and if you really need them, you should do
them on its own separate thread.  One can say that the behavior within
``thread.atomic`` looks, in a way, like the opposite of the usual
effects of the GIL: if the ``with`` block is computationally intensive
it will nicely be parallelized, but if it does any long I/O then it
prevents any parallel work.)


Implementation
==============

XXX


.. include:: _ref.txt
