==========================
What's new in PyPy3 7.3.3+
==========================

.. this is the revision after release-pypy3.6-v7.3.3
.. startrev: a57ea1224248

.. branches merged to py3.6 and are not reported in the test. Re-enable
    these lines for the release or when fixing the test
    .. branch: py3.6-resync

    .. branch: fix-crypt-py3-import

    Fix bad merge of crypt cffi module

    .. branch: issue3348

    Fix utf_8_decode for final=False, error=ignore

.. branch: py3.7-rsre

Fix rsre module for python 3.7

.. branch: incremental_decoder

Fix utf_8_decode for final=False 


.. branch: refactor-posonly

Refactor how positional-only arguments are represented in signature objects,
which brings it more in line with Python 3.8, and simplifies the code.

.. branch: const

Change `char *`` to ``const char *`` in ``PyStructSequence_Field``,
``PyStructSequence_Desc``, ``PyGetSetDef``, ``wrapperbase``

.. branch: win64-py3.7

Merge win64 into this branch

.. branch: win64-cpyext

Fix the cpyext module for win64
