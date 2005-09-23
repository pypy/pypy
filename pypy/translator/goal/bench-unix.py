# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pypy-* files is expected.

import os, sys

current_result = '''
executable                       richards              pystone
pypy-c-17758                     416740ms (326.85x)      916ms (  0.03x)
pypy-c-17797                     394070ms (309.07x)    99999ms (  3.40x)
pypy-llvm-17758                  343870ms (269.70x)     1131ms (  0.04x)
pypy-llvm-17792                  277630ms (217.75x)     1418ms (  0.05x)
pypy-llvm-17797                  274470ms (215.27x)     1434ms (  0.05x)
pypy-llvm-17799                  999990ms (784.31x)    99999ms (  3.40x)
python 2.4.2c1                     1275ms (  1.00x)    29411ms (  1.00x)
'''

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
RICHARDS_CMD = 'from richards import *;Richards.iterations=%d;main()'
RICHARDS_PATTERN = 'Average time for iterations:'

def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        print 'warning: this is no valid output'
        return 99999.0
    return float(line.split()[len(pattern.split())])

def run_cmd(cmd):
    print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    result = pipe.read()
    #print "done"
    return result

def run_pystone(executable='python', n=0):
    argstr = PYSTONE_CMD % (str(n) and n or '')
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, PYSTONE_PATTERN)
    #print res
    return res

def run_richards(executable='python', n=10):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, RICHARDS_PATTERN) * 10 / n
    #print res
    return res

def get_executables():
    exes = [os.path.join('.', name) for name in os.listdir('.') if name.startswith('pypy-')]
    exes.sort()
    return exes

HEADLINE = '''executable                       richards              pystone'''
FMT = '''%-30s   %6dms (%6.2fx)   %6dms (%6.2fx)'''

def main():
    #print 'getting the richards reference'
    ref_rich = run_richards()
    #print 'getting the pystone reference'
    ref_stone = run_pystone()
    res = []
    for exe in get_executables():
        exename = os.path.splitext(exe)[0].lstrip('./')
        res.append( (exename, run_richards(exe, 1), run_pystone(exe)) )
    res.append( ('python %s' % sys.version.split()[0], ref_rich, ref_stone) )
    print HEADLINE
    for exe, rich, stone in res:
        print FMT % (exe, rich, rich / ref_rich, stone, stone / ref_stone)

if __name__ == '__main__':
    main()
