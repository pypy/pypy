# Empty

# XXX Should be empty again, soon.
# XXX hack for win64:
# This patch must stay here until the END OF STAGE 1
# When all tests work, this branch will be merged
# and the branch stage 2 is started, where we remove this patch.
import sys
if hasattr(sys, "maxsize"):
    if sys.maxint != sys.maxsize:
        sys.maxint = sys.maxsize
        import warnings
        warnings.warn("""\n
---> This win64 port is now in stage 1: sys.maxint was modified.
---> When pypy/__init__.py becomes empty again, we have reached stage 2.
""")
