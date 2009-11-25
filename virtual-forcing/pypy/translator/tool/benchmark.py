import autopath
from pypy.tool import testit
from pypy.tool.udir import udir
from pypy.translator.tool.cbuild import build_cfunc
from pypy.translator.test.test_cltrans import global_cl, make_cl_func

def benchmark(func):
    try:
        func = func.im_func
    except AttributeError:
        pass
    c_func = build_cfunc(func, dot=False)
    if global_cl:
        cl_func = make_cl_func(func)
    print "generated c-func for", func.func_name
    t1 = timeit(100, func)
    t2 = timeit(100, c_func)
    if global_cl:
        t3 = timeit(100, cl_func)
    print "cpython func       ", t1, "seconds"
    print "pypy/pyrex/cmodule ", t2, "seconds"
    if global_cl:
        print "cl (experimental)  ", t3, "seconds", global_cl
   
def timeit(num, func, *args):
    from time import time as now
    start = now()
    for i in xrange(num):
        func(*args)
    return now()-start

if __name__ == '__main__':
    from pypy.translator.test.snippet import sieve_of_eratosthenes
    benchmark(sieve_of_eratosthenes)
