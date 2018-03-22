import time
import py
py.path.local(__file__)
from rpython.jit.backend.hlinfo import highleveljitinfo

from rpython.rlib.jit import JitDriver, elidable_compatible, elidable, promote


"""
Run as
$ ./targetcompatible-c $guard 100000000 $objs $res

where $objs is the number of object instances that are created and passed to
the pure function, and $res is the maximum number of different results (one per
object). $guard can be 1 for testing guard_compatible and 2 for guard_value. """


driver1 = JitDriver(greens=[], reds=['n'])
def run1(n):
    while n > 0:
        driver1.can_enter_jit(n=n)
        driver1.jit_merge_point(n=n)
        n -= 1


# "representative case with guard_compatible":
driver2 = JitDriver(greens=[], reds=['n', 's', 'xs'], is_recursive=True)

class A:
    def __init__(self, i):
        self.i = i

@elidable_compatible()
def ec_f2(x):
    return x.i

def run2(n, xs):
    s = 0
    while n > 0:
        driver2.can_enter_jit(n=n, s=s, xs=xs)
        driver2.jit_merge_point(n=n, s=s, xs=xs)
        x = xs[n % len(xs)]
        s += ec_f2(x)
        n -= 1
    return s



# "representative case with guard_value":
driver3 = JitDriver(greens=[], reds=['n', 's', 'xs'], is_recursive=True)

class A:
    def __init__(self, i):
        self.i = i

@elidable
def ec_f3(x):
    return x.i

def run3(n, xs):
    s = 0
    while n > 0:
        driver3.can_enter_jit(n=n, s=s, xs=xs)
        driver3.jit_merge_point(n=n, s=s, xs=xs)
        x = xs[n % len(xs)]
        promote(x)
        s += ec_f3(x)
        n -= 1
    return s


def entry_point(args):
    # store args[0] in a place where the JIT log can find it (used by
    # viewcode.py to know the executable whose symbols it should display)
    exe = args[0]
    args = args[1:]
    highleveljitinfo.sys_executable = exe

    select = int(args[0])
    n = int(args[1])
    objects = int(args[2])
    results = int(args[3])

    xs = [A(i % results) for i in range(objects)]

    print "warming up..."
    if select == 0:
        run1(n)
    elif select == 1:
        run2(n, xs)
    elif select == 2:
        run3(n, xs)

    print "run..."
    
    start = time.clock()
    if select == 0:
        run1(n)
    elif select == 1:
        run2(n, xs)
    elif select == 2:
        run3(n, xs)
    stop = time.clock()
    print 'Warmup jitted: (%f seconds)' % (stop - start)


    return 0



def target(driver, args):
    return entry_point

# ____________________________________________________________

if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
