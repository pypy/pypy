=========================
What's new in PyPy 5.1+
=========================

.. this is a revision shortly after release-5.1
.. startrev: 2180e1eaf6f6

.. branch: rposix-for-3

Reuse rposix definition of TIMESPEC in rposix_stat, add wrapper for fstatat().
This updates the underlying rpython functions with the ones needed for the 
py3k branch
 
.. branch: numpy_broadcast

Add broadcast to micronumpy
