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
