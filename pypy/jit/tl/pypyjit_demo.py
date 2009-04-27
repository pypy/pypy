def do():
    import test.regrtest, sys
    sys.argv = ['regrtest.py', 'test_builtin']
    test.regrtest.main()

try:
    do()
except BaseException, e:
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
