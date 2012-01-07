REVIEW NOTES
============

* ``namespace=locals()``, can we please not use ``locals()``, even in tests?  I find it super hard to read, and it's bad for the JIT.
* Don't we already have a thing named portal (portal call maybe?) is the name confusing?
* ``interp_reso.pyp:wrap_greenkey()`` should do something useful on non-pypyjit jds.
* The ``WrappedOp`` constructor doesn't make much sense, it can only create an op with integer args?
* Let's at least expose ``name`` on ``WrappedOp``.
* DebugMergePoints don't appears to get their metadata.
* Someone else should review the annotator magic.
* Are entry_bridge's compiled seperately anymore? (``set_compile_hook`` docstring)

