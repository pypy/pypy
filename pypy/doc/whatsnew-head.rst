==========================
What's new in PyPy2.7 7.1+
==========================

.. this is a revision shortly after release-pypy-7.1.0
.. startrev: d3aefbf6dae7

.. branch: Twirrim/minor-typo-fix-1553456951526

Fix typo

.. branch: jit-cleanup

Remove rpython.jit.metainterp.typesystem and clean up related code in rpython/jit/

.. branch: datetime_api_27

Add ``DateTime_FromTimestamp`` and ``Date_FromTimestamp``

.. branch: semlock-deadlock

Test and reduce the probability of a deadlock when acquiring a semaphore by
moving global state changes closer to the actual aquire.
