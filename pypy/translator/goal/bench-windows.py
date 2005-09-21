# benchmarks on a windows machine.
# to be executed in the goal folder,
# where a couple of .exe files is expected.

current_result = """
executable                  abs.richards   abs.pystone   rel.rich   rel.pystone
pypy-c-17439-hi               35135 ms        674.191      42.4           60.7
pypy-c-17439-lo               36062 ms        972.900      43.6           42.1
pypy-c-17600-lo               26357 ms        905.379      31.8           45.2
pypy-c-17634-lo               20098 ms       1016.890      24.3           40.3
pypy-c-17649-lo               22637 ms       1041.480      27.3           39.3
pypy-c-17674-hi               15812 ms       2114.430      19.1           19.4
pypy-c-17674-lo               19253 ms       1356.470      23.3           30.2
pypy-c-17707-hi-range         14265 ms       2906.260      17.2           14.1
pypy-c-17707-hi               14105 ms       2120.210      17.0           19.3
pypy-c-17707-lo-range         18701 ms       2834.690      22.6           14.4
pypy-c-17707-lo               19042 ms       1357.690      23.0           30.2
python 2.3.3                    828 ms      40934.500       1.0            1.0

After implementing range at interp-level, results have changed
quite dramatically. Revision 17707 runs everywhere fastest
without the -t-lowmem option. This is probably different on machines
with less than 2 MB of L2-cache.
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
