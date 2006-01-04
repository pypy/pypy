# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pypy-* files is expected.

import os, sys, time

MAX_BENCHMARKS = 40
PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'

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
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='/usr/local/bin/python', n=10):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    return get_result(txt, RICHARDS_PATTERN)

def get_executables():  #sorted by revision number (highest first)
    exes = [os.path.join('.', name) for name in os.listdir('.') if name.startswith('pypy-')]
    exes = [(s.split('-',2)[2], s) for s in exes]
    exes.sort()
    exes.reverse()
    exes = [s[1] for s in exes]
    return exes

HEADLINE = 'date                       executable                        richards             pystone'
FMT      = '%-26s %-30s   %6dms (%6.2fx)   %6d (%6.2fx)'

def main():
    print HEADLINE
    sys.stdout.flush()
    ref_rich = run_richards()
    ref_stone = run_pystone()
    print FMT % (time.ctime(), 'python %s' % sys.version.split()[0], ref_rich, 1.0, ref_stone, 1.0)
    sys.stdout.flush()
    for exe in get_executables()[:MAX_BENCHMARKS]:
        exename = os.path.splitext(exe)[0].lstrip('./')
        ctime   = time.ctime( os.path.getctime(exename) )
        rich    = run_richards(exe, 1)
        stone   = run_pystone(exe)
        print FMT % (ctime, exename, rich, rich / ref_rich, stone, ref_stone / stone)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
