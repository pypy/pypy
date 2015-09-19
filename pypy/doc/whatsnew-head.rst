=======================
What's new in PyPy 2.6+
=======================

.. this is a revision shortly after release-2.6.1
.. startrev: 07769be4057b

.. branch: keys_with_hash
Improve the performance of dict.update() and a bunch of methods from
sets, by reusing the hash value stored in one dict when inspecting
or changing another dict with that key.

.. branch: optresult-unroll 
A major refactoring of the ResOperations that kills Box. Also rewrote
unrolling to enable future enhancements.  Should improve warmup time
by 20% or so.

.. branch: optimize-cond-call
Optimize common sequences of operations like
``int_lt/cond_call`` in the JIT backends

.. branch: missing_openssl_include
Fix for missing headers in OpenBSD, already applied in downstream ports

.. branch: gc-more-incremental
Remove a source of non-incremental-ness in the GC: now
external_malloc() no longer runs gc_step_until() any more. If there
is a currently-running major collection, we do only so many steps
before returning. This number of steps depends on the size of the
allocated object. It is controlled by tracking the general progress
of these major collection steps and the size of old objects that
keep adding up between them.
