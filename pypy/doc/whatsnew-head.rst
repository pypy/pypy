==========================
What's new in PyPy2.7 5.6+
==========================

.. this is a revision shortly after release-pypy2.7-v5.6
.. startrev: 7e9787939641

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
