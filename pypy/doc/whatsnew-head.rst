==========================
What's new in PyPy2.7 5.9+
==========================

.. this is a revision shortly after release-pypy2.7-v5.8.0
.. startrev: 558bd00b3dd8

.. branch: cffi-complex
.. branch: cffi-char16-char32

The two ``cffi-*`` branches are part of the upgrade to cffi 1.11.

.. branch: ctypes_char_indexing

Indexing into char* behaves differently than CPython

.. branch: vmprof-0.4.8

Improve and fix issues with vmprof

.. branch: issue-2592

CPyext PyListObject.pop must return the value

.. branch: cpyext-hash_notimpl

If ``tp_hash`` is ``PyObject_HashNotImplemented``, set ``obj.__dict__['__hash__']`` to None
