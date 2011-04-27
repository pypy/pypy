==========================
Garbage Collection in PyPy
==========================

.. contents::


Introduction
============

**Warning**: The overview and description of our garbage collection
strategy and framework is not here but in the `EU-report on this
topic`_.  The present document describes the specific garbage collectors
that we wrote in our framework.

.. _`EU-report on this topic`: http://codespeak.net/pypy/extradoc/eu-report/D07.1_Massive_Parallelism_and_Translation_Aspects-2007-02-28.pdf


Garbage collectors currently written for the GC framework
=========================================================

XXX we need to add something about minimark

(Very rough sketch only for now.)

Reminder: to select which GC you want to include in a translated
RPython program, use the ``--gc=NAME`` option of ``translate.py``.
For more details, see the `overview of command line options for
translation`_.

.. _`overview of command line options for translation`: config/commandline.html#translation

Mark and Sweep
--------------

Classical Mark and Sweep collector.  Also contains a lot of experimental
and half-unmaintained features.  See `pypy/rpython/memory/gc/marksweep.py`_.

Semispace copying collector
---------------------------

Two arenas of equal size, with only one arena in use and getting filled
with new objects.  When the arena is full, the live objects are copied
into the other arena using Cheney's algorithm.  The old arena is then
cleared.  See `pypy/rpython/memory/gc/semispace.py`_.

On Unix the clearing is done by reading ``/dev/zero`` into the arena,
which is extremely memory efficient at least on Linux: it lets the
kernel free the RAM that the old arena used and replace it all with
allocated-on-demand memory.

The size of each semispace starts at 8MB but grows as needed when the
amount of objects alive grows.

Generational GC
---------------

This is a two-generations GC.  See `pypy/rpython/memory/gc/generation.py`_.

It is implemented as a subclass of the Semispace copying collector.  It
adds a nursery, which is a chunk of the current semispace.  Its size is
computed to be half the size of the CPU Level 2 cache.  Allocations fill
the nursery, and when it is full, it is collected and the objects still
alive are moved to the rest of the current semispace.

The idea is that it is very common for objects to die soon after they
are created.  Generational GCs help a lot in this case, particularly if
the amount of live objects really manipulated by the program fits in the
Level 2 cache.  Moreover, the semispaces fill up much more slowly,
making full collections less frequent.

Hybrid GC
---------

This is a three-generations GC.

It is implemented as a subclass of the Generational GC.  The Hybrid GC
can handle both objects that are inside and objects that are outside the
semispaces ("external").  The external objects are not moving and
collected in a mark-and-sweep fashion.  Large objects are allocated as
external objects to avoid costly moves.  Small objects that survive for
a long enough time (several semispace collections) are also made
external so that they stop moving.

This is coupled with a segregation of the objects in three generations.
Each generation is collected much less often than the previous one.  The
division of the generations is slightly more complicated than just
nursery / semispace / external; see the diagram at the start of the
source code, in `pypy/rpython/memory/gc/hybrid.py`_.

Mark & Compact GC
-----------------

Inspired, at least partially, by Squeak's garbage collector, this is a
single-arena GC in which collection compacts the objects in-place.  The
main point of this GC is to save as much memory as possible (to be not
worse than the Semispace), but without the peaks of double memory usage
during collection.

Unlike the Semispace GC, collection requires a number of passes over the
data.  This makes collection quite slower.  Future improvements could be
to add a nursery to Mark & Compact in order to mitigate this issue.

During a collection, we reuse the space in-place if it is still large
enough.  If not, we need to allocate a new, larger space, and move the
objects there; however, this move is done chunk by chunk, and chunks are
cleared (i.e. returned to the OS) as soon as they have been moved away.
This means that (from the point of view of the OS) a collection will
never cause an important temporary growth of total memory usage.

More precisely, a collection is triggered when the space contains more
than N*M bytes, where N is the number of bytes alive after the previous
collection and M is a constant factor, by default 1.5.  This guarantees
that the total memory usage of the program never exceeds 1.5 times the
total size of its live objects.

The objects themselves are quite compact: they are allocated next to
each other in the heap, separated by a GC header of only one word (4
bytes on 32-bit platforms) and possibly followed by up to 3 bytes of
padding for non-word-sized objects (e.g. strings).  There is a small
extra memory usage during collection: an array containing 2 bytes per
surviving object is needed to make a backup of (half of) the surviving
objects' header, in order to let the collector store temporary relation
information in the regular headers.

More details are available as comments at the start of the source
in `pypy/rpython/memory/gc/markcompact.py`_.

.. include:: _ref.txt
