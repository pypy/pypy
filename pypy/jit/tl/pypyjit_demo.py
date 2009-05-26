TESTNAME = 'test_builtin'


def do():
    __import__('test.' + TESTNAME)
    print "---ending 1---"

def simple_loop():
    print "simple loop"
    i = 0
    N = 100
    step = 3
    while i < N:
        i = i + step
    print i

def g(i):
    for k in range(i, i +2):
        pass

def loop():
    for i in range(10000):
        g(i)

try:
    #do()
    loop()
    print "---ending 2---"
except BaseException, e:
    print "---ending 0---"
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
