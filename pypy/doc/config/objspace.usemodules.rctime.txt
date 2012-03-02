Use the 'rctime' module. 

'rctime' is our `rffi`_ based implementation of the builtin 'time' module.
It supersedes the less complete :config:`objspace.usemodules.time`,
at least for C-like targets (the C and LLVM backends).

.. _`rffi`: ../rffi.html
