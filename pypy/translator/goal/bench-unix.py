# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pypy-* files is expected.

import os, sys

current_result = '''
executable                        richards             pystone
python 2.4.2c1                      864ms (  1.00x)    43103 (  1.00x)
pypy-llvm-17870                   12574ms ( 14.55x)     3069 ( 14.04x)
pypy-llvm-17862                   12980ms ( 15.02x)     3041 ( 14.17x)
pypy-llvm-17797                   13473ms ( 15.59x)     2824 ( 15.26x)
pypy-llvm-17792                   13755ms ( 15.92x)     2823 ( 15.27x)
pypy-llvm-17758                   17057ms ( 19.74x)     2229 ( 19.34x)
pypy-c-17853                      22411ms ( 25.94x)     1653 ( 26.07x)
pypy-c-17806                      22315ms ( 25.83x)     1656 ( 26.03x)
pypy-c-17758                      23500ms ( 27.20x)     1570 ( 27.45x)
'''

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

def run_pystone(executable='python', n=0):
    argstr = PYSTONE_CMD % (str(n) and n or '')
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='python', n=10):
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

HEADLINE = 'executable                        richards             pystone'
FMT      = '%-30s   %6dms (%6.2fx)   %6d (%6.2fx)'

def main():
    print HEADLINE
    sys.stdout.flush()
    ref_rich = run_richards()
    ref_stone = run_pystone()
    print FMT % ('python %s' % sys.version.split()[0], ref_rich, 1.0, ref_stone, 1.0)
    sys.stdout.flush()
    for exe in get_executables():
        exename = os.path.splitext(exe)[0].lstrip('./')
        rich    = run_richards(exe, 1)
        stone   = run_pystone(exe)
        print FMT % (exename, rich, rich / ref_rich, stone, ref_stone / stone)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
