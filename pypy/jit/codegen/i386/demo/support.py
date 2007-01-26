import os, sys
import py
from pypy.tool.udir import udir
from pypy.rlib.ros import putenv
from pypy.jit.codegen.graph2rgenop import rcompile
from pypy.jit.codegen.i386.rgenop import RI386GenOp
from pypy.jit.codegen.i386.codebuf import machine_code_dumper
from ctypes import cast, c_void_p, CFUNCTYPE, c_int

from pypy import conftest
from pypy.jit import conftest as bench_conftest
from pypy.jit.codegen.i386.demo import conftest as demo_conftest


def Random():
    import random
    seed = demo_conftest.option.randomseed
    print
    print 'Random seed value is %d.' % (seed,)
    print
    return random.Random(seed)


def rundemo(entrypoint, *args):
    view = conftest.option.view
    seed = demo_conftest.option.randomseed
    benchmark = bench_conftest.option.benchmark

    logfile = str(udir.join('%s.log' % (entrypoint.__name__,)))
    try:
        os.unlink(logfile)
    except OSError:
        pass
    putenv('PYPYJITLOG=' + logfile)

    if benchmark:
        py.test.skip("benchmarking: working in progress")
        arglist = ', '.join(['a%d' % i for i in range(len(args))])
        miniglobals = {'Benchmark': bench_conftest.Benchmark,
                       'original_entrypoint': entrypoint}
        exec py.code.Source("""
            def benchmark_runner(%s):
                bench = Benchmark()
                while 1:
                    res = original_entrypoint(%s)
                    if bench.stop():
                        break
                return res
        """ % (arglist, arglist)).compile() in miniglobals
        entrypoint = miniglobals['benchmark_runner']

    nb_args = len(args)      # XXX ints only for now
    machine_code_dumper._freeze_()    # clean up state
    rgenop = RI386GenOp()
    gv_entrypoint = rcompile(rgenop, entrypoint, [int]*nb_args,
                             random_seed=seed)
    machine_code_dumper._freeze_()    # clean up state

    print
    print 'Random seed value: %d' % (seed,)
    print

    print 'Running %s(%s)...' % (entrypoint.__name__,
                                 ', '.join(map(repr, args)))
    expected = entrypoint(*args)
    print 'Python ===>', expected
    fp = cast(c_void_p(gv_entrypoint.value),
              CFUNCTYPE(c_int, *[c_int] * nb_args))
    res = fp(*args)
    print 'i386   ===>', res
    print
    if res != expected:
        raise AssertionError(
            "expected return value is %s, got %s\nseed = %s" % (
                expected, res, seed))

    if view:
        from pypy.jit.codegen.i386.viewcode import World
        world = World()
        world.parse(open(logfile))
        world.show()
