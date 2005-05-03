import sys
from test import test_support 
test_support.verbose = False
sys.argv[:] = sys.argv[1:]
execfile(sys.argv[0])
