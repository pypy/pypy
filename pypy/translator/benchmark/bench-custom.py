# benchmarks on a unix machine.

import autopath
from pypy.translator.benchmark.result import BenchmarkResultSet
from pypy.translator.benchmark.benchmarks import BENCHMARKS
import os, sys, time, pickle, re, py

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

    benchmarks = [b for b in BENCHMARKS if b.name in options.benchmarks]

    exes = get_executables(args)
    pythons = 'python2.5 python2.4 python2.3'.split()
    full_pythons = []
    for python in pythons:
        full_python = py.path.local.sysfind(python)
        if full_python:
            full_pythons.append(str(full_python))

    sys.stdout.flush()

    refs = {}

    exes = full_pythons+exes

    for i in range(int(options.runcount)):
        for exe in full_pythons+exes:
            for b in benchmarks:
                benchmark_result.result(exe).run_benchmark(b, verbose=True)

    stats = ['stat:st_mtime', 'exe_name', 'bench:richards', 'pypy_rev', 'bench:pystone']
    for row in benchmark_result.txt_summary(stats,
                                            relto=full_pythons[0],
                                            filteron=lambda r: r.exe_name in exes):
        print row

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option(
        '--benchmarks', dest='benchmarks',
        default=','.join([b.name for b in BENCHMARKS])
        )
    parser.add_option(
        '--pickle', dest='picklefile',
        default='bench-custom.benchmark_result'
        )
    parser.add_option(
        '--runcount', dest='runcount',
        default='1',
        )
    options, args = parser.parse_args(sys.argv[1:])
    main(options, args)
