# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pypy-* files is expected.

import os, sys, time, pickle

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
PYSTONE_ASCENDING_GOOD = True

RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'
RICHARDS_ASCENDING_GOOD = False

class BenchmarkResult(object):

    def __init__(self, filename, max_results=10):
        self.filename    = filename
        self.max_results = max_results
        if os.path.exists(filename):
            f = open(filename, 'r')
            self.n_results   = pickle.load(f)
            self.best_result = pickle.load(f)
            f.close()
            # any exception while loading the file is best reported
            # as a crash, instead of as a silent loss of all the
            # data :-/
        else:
            self.n_results   = {}
            self.best_result = {}

    def is_stable(self, name):
        try:
            return self.n_results[name] >= self.max_results
        except:
            return False

    def update(self, name, result, ascending_good):
        try:
            if ascending_good:
                self.best_result[name] = max(self.best_result[name], result)
            else:
                self.best_result[name] = min(self.best_result[name], result)
        except KeyError:
            self.n_results[name] = 0
            self.best_result[name] = result
        self.n_results[name] += 1

        f = open(self.filename, 'w')
        pickle.dump(self.n_results  , f)
        pickle.dump(self.best_result, f)
        f.close()

    def get_best_result(self, name):
        return self.best_result[name]


def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        print 'warning: this is no valid output'
        return 99999.0
    return float(line.split()[len(pattern.split())])

def run_cmd(cmd):
    #print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    return pipe.read()

def run_pystone(executable='/usr/local/bin/python', n=0):
    argstr = PYSTONE_CMD % (str(n) and n or '')
    txt = run_cmd('"%s" -c "%s"' % (executable, argstr))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='/usr/local/bin/python', n=5):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('"%s" -c "%s"' % (executable, argstr))
    return get_result(txt, RICHARDS_PATTERN)

def get_executables():  #sorted by revision number (highest first)
    exes = []
    for exe in [os.path.join('.', name) for name in os.listdir('.') if name.startswith('pypy-')]:
        if os.path.isdir(exe) or exe.endswith('.jar'):
            continue
        try:
            exes.append( (exe.split('-')[2], exe) )
        except:
            pass    #skip filenames without version number
    exes.sort()
    exes.reverse()
    exes = [s[1] for s in exes]
    return exes

def main():
    benchmark_result = BenchmarkResult('bench-unix.benchmark_result')

    print 'date                           size codesize    executable                                                      richards            pystone'
    sys.stdout.flush()

    ref_rich, ref_stone = None, None

#    for exe in '/usr/local/bin/python2.5 python2.4 python2.3'.split():
    for exe in 'python2.4 python2.3'.split():
        v = os.popen(exe + ' -c "import sys;print sys.version.split()[0]"').read().strip()
        if not v:
            continue
        r = v + '_richards'
        if not benchmark_result.is_stable(r):
            benchmark_result.update(r, run_richards(exe), RICHARDS_ASCENDING_GOOD)
        rich = benchmark_result.get_best_result(r)
        if not ref_rich:
            ref_rich = rich

        p = v + '_pystone'
        if not benchmark_result.is_stable(p):
            benchmark_result.update(p, run_pystone(exe), PYSTONE_ASCENDING_GOOD)
        stone = benchmark_result.get_best_result(p)
        if not ref_stone:
            ref_stone = stone

        fmt = '%-26s %8s %8s    <a href="microbench-archive/%s.txt">%-60s</a>   %6dms (%6.1fx)   %6d (%6.1fx)'
        print fmt % (time.ctime(), '-', '-', 'python', 'CPython ' + v, rich, rich / ref_rich, stone, stone / ref_stone)
        sys.stdout.flush()

    for exe in get_executables():
        exename = os.path.splitext(exe)[0].lstrip('./')
        ctime   = time.ctime( os.path.getmtime(exename) )

        #compute microbenchmark results (only once)
        f = '../microbench/archive/%s.txt' % exe
        if not os.path.exists(f) or os.stat(f).st_size < 100:
            os.chdir('../microbench')
            run_cmd('python2.4 ./microbench.py python2.4 "../goal/%s" > "archive/%s.txt"' % (exe, exe))
            os.chdir('../goal')
            
        r = exe + '_richards'
        if not benchmark_result.is_stable(r):
            #continue with our regular benchmarks
            benchmark_result.update(r, run_richards(exe, 1), RICHARDS_ASCENDING_GOOD)
        rich = benchmark_result.get_best_result(r)

        p = exe + '_pystone'
        if not benchmark_result.is_stable(p):
            benchmark_result.update(p, run_pystone(exe), PYSTONE_ASCENDING_GOOD)
        stone = benchmark_result.get_best_result(p)

        if 'pypy-cli' in exename:
            dirname = exename + '-data'
            codesize = 'N/A'
            try:
                exesize = os.path.getsize(os.path.join(dirname, 'main.exe'))
            except OSError:
                exesize = 'XXX'
        elif 'pypy-jvm' in exename:
            jarname = exename + '.jar'
            codesize = 'N/A'
            try:
                exesize = os.path.getsize(jarname)
            except OSError:
                exesize = 'XXX'
        else:
            codesize = os.popen('size "%s" | tail -n1 | cut -f1'%(exename,)).read().strip()
            exesize = os.path.getsize(exe)

        print fmt % (ctime, exesize, codesize, exename, exename, rich, rich / ref_rich, stone, ref_stone / stone)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
