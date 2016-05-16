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

.. branch: z196-support

Fixes a critical issue in the register allocator and extends support on s390x. PyPy runs and translates on
the s390x revisions z10 (released February 2008, experimental) and z196 (released August 2010)
) in addition to zEC12 and z13.
