=========================
What's new in PyPy 4.0.+
=========================

.. this is a revision shortly after release-4.0.0
.. startrev: 9397d7c6f5aa

.. branch: lazy-fast2locals
improve the performance of simple trace functions by lazily calling
fast2locals and locals2fast only if f_locals is actually accessed.
