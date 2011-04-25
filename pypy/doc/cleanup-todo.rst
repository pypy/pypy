
PyPy cleanup areas
==================

This is a todo list that lists various areas of PyPy that should be cleaned up
(for whatever reason: less mess, less code duplication, etc).

translation toolchain
---------------------

 - low level backends should share more code
 - all backends should have more consistent interfaces
 - delegate finding type stuff like vtables etc to GC, cleaner interface for rtti,
   simplify translator/c/gc.py
 - clean up the tangle of including headers in the C backend
 - make approach for loading modules more sane, mixedmodule capture
   too many platform dependencies especially for pypy-cli
 - review pdbplus, especially the graph commands, also in the light of
   https://codespeak.net/issue/pypy-dev/issue303 and the fact that
   we can have more than one translator/annotator around (with the
   timeshifter)

interpreter
-----------

 - review the things implemented at applevel whether they are performance-
   critical

 - review CPython regression test suite, enable running tests, fix bugs
