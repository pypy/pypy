# Empty
# XXX Should be empty again, soon.
# XXX hack for win64:
# This patch must stay here until the ENDS OF STAGE 1
# When all tests work, this branch will be merged
# and the branch stage 2 is started, where we remove this patch.
import sys
if hasattr(sys, "maxsize"):
    sys.maxint = max(sys.maxint, sys.maxsize)
