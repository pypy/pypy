# benchmarks on a windows machine.
# to be executed in the goal folder,
# where a couple of .exe files is expected.

current_result = """
executable                  abs.richards   abs.pystone   rel.rich   rel.pystone
pypy-c-17439-hi               35415 ms        620.652      42.6           65.4
pypy-c-17439-lo               36492 ms        923.530      43.9           44.0
pypy-c-17600-lo               26542 ms        893.093      31.9           45.5
pypy-c-17634-lo               20203 ms       1001.520      24.3           40.6
pypy-c-17649-lo               22792 ms       1028.290      27.4           39.5
pypy-c-17674-hi               15927 ms       1934.000      19.1           21.0
pypy-c-17674-lo               17009 ms       1283.800      20.4           31.6
pypy-c-17707-hi               15942 ms       1971.950      19.2           20.6
python 2.3.3                    832 ms      40612.100       1.0            1.0

This time, more comparisons between -t-lowmem and without it (using geninterp
as much as possible) were done. It is interesting how much translation of
geninterp'ed code is accelerated, now. Note that range() is still at applevel,
but very efficiently translated. It will anyway be moved to interplevel
next time, it is too frequently used.
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
    import win32con, win32process
    curr = win32process.GetCurrentProcess()
    prio = win32con.HIGH_PRIORITY_CLASS
    win32process.SetPriorityClass(curr, prio)
    # unfortunately, the above doesn't help, because the process priority
    # is not inherited by child process. We also cannot import WIn32 extensions
    # right now, since PyPycanot handle extension modules.
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
