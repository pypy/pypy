# benchmarks on a windows machine.
# to be executed in the goal folder,
# where a couple of .exe files is expected.

current_result = """
executable                  abs.richards   abs.pystone   rel.rich   rel.pystone
pypy-c-17439                  35165 ms         668.586      42.4           61.1
pypy-c-17600                  26388 ms         900.481      31.8           45.4
pypy-c-17634                  20108 ms        1017.720      24.2           40.1
pypy-c-17649                  22662 ms        1035.910      27.3           39.4
pypy-c-17674-nolowmem         15817 ms        1981.470      19.1           20.6
pypy-c-17674-t-lowmem         16834 ms        1274.650      20.3           32.1
python 2.3.3                    830 ms       40861.400       1.0            1.0

17649 was with explicit fixed stack.
Changes after 17634 we not included.
17674 has an outrageous effect. I cannot really
find out what it was. Did Armin do the fixed stack
patch already? Probably not. Was it Samuele's avoiding
of duplicate zeroing? Really just that? I think so, and
this is incredible.
Even more incredible is the fact that not using using
t-lowmem accelerates pystone so much. This is an indicator
that we missed something used in pystone that still contains
applevel code. I can't believe it, will find it tomorrow.
"""

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

def run_richards(executable='python', n=20):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, RICHARDS_PATTERN)
    print res
    return res

def get_executables():
    exes = [name for name in os.listdir('.') if name.endswith('.exe')]
    exes.sort()
    return exes

HEADLINE = '''\
executable                  abs.richards   abs.pystone   rel.rich   rel.pystone'''
FMT = '''\
%-27s   '''                 +  '%5d ms      %9.3f     ' + '%5.1f          %5.1f'

def main():
    print 'getting the richards reference'
    ref_rich = run_richards()
    print 'getting the pystone reference'
    ref_stone = run_pystone()
    res = []
    for exe in get_executables():
        exename = os.path.splitext(exe)[0]
        res.append( (exename, run_richards(exe, 2), run_pystone(exe, 20000)) )
    res.append( ('python %s' % sys.version.split()[0], ref_rich, ref_stone) )
    print HEADLINE
    for exe, rich, stone in res:
        print FMT % (exe, rich, stone, rich / ref_rich, ref_stone / stone)

if __name__ == '__main__':
    main()
