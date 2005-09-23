# benchmarks on a unix machine.
# to be executed in the goal folder,
# where a couple of pyp-c* files is expected.

import os, sys

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
RICHARDS_CMD = 'from richards import *;Richards.iterations=%d;main()'
RICHARDS_PATTERN = 'Average time for iterations:'

def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        raise ValueError, 'this is no valid output'
    return float(line.split()[len(pattern.split())])

def run_cmd(cmd):
    print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    result = pipe.read()
    print "done"
    return result

def run_pystone(executable='python', n=0):
    argstr = PYSTONE_CMD % (str(n) and n or '')
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, PYSTONE_PATTERN)
    print res
    return res

def run_richards(executable='python', n=10):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, RICHARDS_PATTERN)
    print res
    return res

def get_executables():
    exes = [os.path.join('.', name) for name in os.listdir('.') if name.startswith('pypy-')]
    exes.sort()
    return exes

HEADLINE = '''\
executable                     abs.richards   abs.pystone   rel.richards   rel.pystone'''
FMT = '''\
%-30s   '''          +  '%5d ms       %9.3f     ' + '%5.1f          %5.1f'

def main():
    print 'getting the richards reference'
    ref_rich = run_richards()
    print 'getting the pystone reference'
    ref_stone = run_pystone()
    res = []
    for exe in get_executables():
        exename = os.path.splitext(exe)[0].lstrip('./')
        res.append( (exename, run_richards(exe, 1), run_pystone(exe, 2000)) )
    res.append( ('python %s' % sys.version.split()[0], ref_rich, ref_stone) )
    print HEADLINE
    for exe, rich, stone in res:
        print FMT % (exe, rich, stone, rich / ref_rich, ref_stone / stone)

if __name__ == '__main__':
    main()
