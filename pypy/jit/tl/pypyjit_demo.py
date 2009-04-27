TESTNAME = 'test_builtin'

def do():
    import test.regrtest, sys
    sys.argv = ['regrtest.py', TESTNAME]
    test.regrtest.main()

try:
    do()
except BaseException, e:
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
