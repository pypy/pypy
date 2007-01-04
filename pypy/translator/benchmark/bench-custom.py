# benchmarks on a unix machine.

import autopath
from pypy.translator.benchmark.result import BenchmarkResult
from pypy.translator.benchmark.benchmarks import BENCHMARKS
import os, sys, time, pickle, re

def get_executables(args):  #sorted by revision number (highest first)
    return sorted(args, key=os.path.getmtime)

def main(options, args):
    benchmark_result = BenchmarkResult('bench-custom.benchmark_result')

    benchmarks = [b for b in BENCHMARKS if b[0] in options.benchmarks]

    exes = get_executables(args)
    pythons = 'python2.4 python2.3'.split()
    width = max(map(len, exes+pythons+['executable'])) + 3

    print 'date                           size codesize    %-*s'%(width, 'executable'),
    for name, run, ascgood, units in benchmarks:
        print '    %-*s'%(6+len(units)+2+8+2-4, name),
    print
    sys.stdout.flush()

    refs = {}

    for exe in pythons+exes:
        exe_ = exe
        if exe in pythons:
            size = codesize = '-'
            ctime = time.ctime()
        else:
            size = os.path.getsize(exe)
            codesize = os.popen('size "%s" | tail -n1 | cut -f1'%(exe,)).read().strip()
            ctime = time.ctime(os.path.getmtime(exe))
            if '/' not in exe:
                exe_ = './' + exe
        print '%-26s %8s %8s    %-*s'%(ctime, size, codesize, width, exe),
        sys.stdout.flush()
        for name, run, ascgood, units in benchmarks:
            n = exe + '_' + name
            if not benchmark_result.is_stable(n):
                benchmark_result.update(n, run(exe_), ascgood)
            res = benchmark_result.get_best_result(n)
            if name not in refs:
                refs[name] = res
            factor = res/refs[name]
            if ascgood:
                factor = 1/factor
            print "%6d%s (%6.1fx)"%(res, units, factor),
            sys.stdout.flush()
        print

        sys.stdout.flush()

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option(
        '--benchmarks', dest='benchmarks',
        default=','.join([b[0] for b in BENCHMARKS])
        )
    options, args = parser.parse_args(sys.argv[1:])
    main(options, args)
