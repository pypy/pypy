==========================
What's new in PyPy2.7 5.6+
==========================

.. this is a revision shortly after release-pypy2.7-v5.6
.. startrev: 7e9787939641


Since a while now, PyPy preserves the order of dictionaries and sets.
However, the set literal syntax ``{x, y, z}`` would by mistake build a
set with the opposite order: ``set([z, y, x])``.  This has been fixed.
Note that CPython is inconsistent too: in 2.7.12, ``{5, 5.0}`` would be
``set([5.0])``, but in 2.7.trunk it is ``set([5])``.  PyPy's behavior
changed in exactly the same way because of this fix.


.. branch: rpython-error-to-systemerror

Any uncaught RPython exception (from a PyPy bug) is turned into an
app-level SystemError.  This should improve the lot of users hitting an
uncaught RPython error.

.. branch: union-side-effects-2

Try to improve the consistency of RPython annotation unions.

.. branch: pytest-2.9.2

.. branch: clean-exported-state

Clean-ups in the jit optimizeopt

.. branch: conditional_call_value_4

Add jit.conditional_call_elidable(), a way to tell the JIT "conditonally
call this function" returning a result.

.. branch: desc-specialize

Refactor FunctionDesc.specialize() and related code (RPython annotator).
