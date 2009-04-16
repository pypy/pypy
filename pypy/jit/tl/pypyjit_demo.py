def simple_loop():
    print "simple loop"

    i = 0
    while i < 100:
        i = i + 3
    print i
    assert i == 102

try:
    simple_loop()
except Exception, e:
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
