"""
Stackless demo.

This example only works on top of a pypy-c compiled with stackless features
and the signal module:

    translate.py --stackless targetpypystandalone --withmod-signal

Usage:

    pypy-c pickle_coroutine.py --start demo.pickle

        Start the computation.  You can interrupt it at any time by
        pressing Ctrl-C; at this point, the state of the computing
        coroutine is saved in demo.pickle.

    pypy-c pickle_coroutine.py --resume demo.pickle

        Reload the coroutine from demo.pickle and continue running it.
        (It can be interrupted again with Ctrl-C.)

This demo is documented in detail in pypy/doc/stackless.txt.
"""

try:
    import sys, pickle, signal
    from stackless import coroutine
except ImportError:
    print __doc__
    sys.exit(2)


def ackermann(x, y):
    check()
    if x == 0:
        return y + 1
    if y == 0:
        return ackermann(x - 1, 1)
    return ackermann(x - 1, ackermann(x, y - 1))

# ____________________________________________________________

main = coroutine.getcurrent()
sys.setrecursionlimit(100000)

interrupt_flag = False

def interrupt_handler(*args):
    global interrupt_flag
    interrupt_flag = True

def check():
    if interrupt_flag:
        main.switch()


def execute(coro):
    signal.signal(signal.SIGINT, interrupt_handler)
    res = coro.switch()
    if res is None and coro.is_alive:    # interrupted!
        print "interrupted! writing %s..." % (filename,)
        f = open(filename, 'w')
        pickle.dump(coro, f)
        f.close()
        print "done"
    else:
        print "result:", res

try:
    operation, filename = sys.argv[1:]
except ValueError:
    print __doc__
    sys.exit(2)

if operation == '--start':
    coro = coroutine()
    coro.bind(ackermann, 3, 7)
    print "running from the start..."
    execute(coro)
elif operation == '--resume':
    print "reloading %s..." % (filename,)
    f = open(filename)
    coro = pickle.load(f)
    f.close()
    print "done, running now..."
    execute(coro)
