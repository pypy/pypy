
=======================
What's new in PyPy 2.5+
=======================

.. this is a revision shortly after release-2.4.x
.. startrev: 7026746cbb1b

.. branch: win32-fixes5
Fix c code generation for msvc so empty "{ }" are avoided in unions,
Avoid re-opening files created with NamedTemporaryFile,
Allocate by 4-byte chunks in rffi_platform,
Skip testing objdump if it does not exist,
and other small adjustments in own tests
