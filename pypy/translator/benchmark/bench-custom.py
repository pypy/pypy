# benchmarks on a unix machine.

import autopath
from pypy.translator.benchmark.result import BenchmarkResultSet
from pypy.translator.benchmark.benchmarks import BENCHMARKS
import os, sys, time, pickle, re, py

SPLIT_TABLE = True      # useful when executable names are very long

def get_executables(args):  #sorted by revision number (highest first)
    exes = sorted(args, key=os.path.getmtime)
    r = []
    for exe in exes:
        if '/' not in exe:
            r.append('./' + exe)
        else:
            r.append(exe)
    return r

def main(options, args):
    if os.path.exists(options.picklefile):
        benchmark_result = pickle.load(open(options.picklefile, 'rb'))
    else:
        benchmark_result = BenchmarkResultSet()

    benchmarks = []
    for b in BENCHMARKS:
        if b.name in options.benchmarks:
            if not b.check():
                print "can't run %s benchmark for some reason"%(b.name,)
            else:
                if int(options.sizefactor) > 1:
                    b = b * int(options.sizefactor)
                benchmarks.append(b)

    exes = get_executables(args)
    pythons = 'python2.6 python2.5 python2.4'.split()
    full_pythons = []
    for python in pythons:
        full_python = py.path.local.sysfind(python)
        if full_python:
            full_pythons.append(str(full_python))

    sys.stdout.flush()

    refs = {}
    final_error_count = 0

    if not options.nocpython:
        exes = full_pythons + exes

    for i in range(int(options.runcount)) or [None]:
        if i is not None:
            for exe in exes:
                for b in benchmarks:
                    br = benchmark_result.result(exe, allowcreate=True)
                    result = br.run_benchmark(b, verbose=options.verbose)
                    if not result:
                        final_error_count += 1

        if options.relto:
            relto = options.relto
        else:
            relto = full_pythons[0]
        if relto not in benchmark_result.benchmarks:
            continue

        pickle.dump(benchmark_result, open(options.picklefile, 'wb'))

        exe_stats = ['stat:st_mtime', 'exe_name', 'pypy_rev']
        if not SPLIT_TABLE:
            stats = exe_stats[:]
        else:
            stats = ['exe']
        for b in benchmarks:
            stats.append('bench:'+b.name)
        kwds = {'relto': relto,
                'filteron' :lambda r: r.exe_name in exes,
                }
        for row in benchmark_result.txt_summary(stats, **kwds):
            print row
        if SPLIT_TABLE:
            print
            print 'Reference:'
            for row in benchmark_result.txt_summary(['exe'] + exe_stats,
                                                    **kwds):
                print row
            print

    if final_error_count:
        raise SystemExit("%d benchmark run(s) failed (see -FAILED- above)"
                         % final_error_count)

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    default_benches = ','.join([b.name for b in BENCHMARKS if b.check()])
    parser.add_option(
        '--benchmarks', dest='benchmarks',
        default=default_benches,
        )
    parser.add_option(
        '--pickle', dest='picklefile',
        default='bench-custom.benchmark_result'
        )
    parser.add_option(
        '--runcount', dest='runcount',
        default='1',
        )
    parser.add_option(
        '--relto', dest='relto',
        default=None,
        )
    parser.add_option(
        '-v', '--verbose', action='store_true', dest='verbose',
        default=None,
        )
    parser.add_option(
        '--no-cpython', action='store_true', dest='nocpython',
        default=None,
        )
    parser.add_option(
        '--size-factor', dest='sizefactor',
        default='1',
        )
    options, args = parser.parse_args(sys.argv[1:])
    main(options, args)
