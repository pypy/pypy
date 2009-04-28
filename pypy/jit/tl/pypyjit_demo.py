TESTNAME = 'test_builtin'

def do():
    __import__('test.' + TESTNAME)
    print "---ending 1---"

try:
    do()
    print "---ending 2---"
except BaseException, e:
    print "---ending 0---"
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
