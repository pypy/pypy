# benchmarks on a windows machine.
# to be executed in the goal folder,
# where a couple of .exe files is expected.

USE_HIGH_PRIORITY = True
# usage with high priority:
# the program will try to import subprocess.
# you can have this with python older than 2.4: copy
# subprocess into lib and change line 392 to use win32

current_result = """
executable                  richards         pystone            size (MB)
pypy-c-17439               37413   47.7x      678.4   60.7x       5.65
pypy-c-17600-lo            26352   33.6x      906.2   45.4x       6.43
pypy-c-17634-lo            20108   25.7x     1023.5   40.2x       6.42
pypy-c-17649-lo            22612   28.9x     1042.0   39.5x       6.41
pypy-c-17674-lo            19248   24.6x     1358.8   30.3x       6.40
pypy-c-17674               12402   15.8x     1941.4   21.2x       7.37
pypy-c-17439-lo            29638   37.8x      971.4   42.4x       6.49
pypy-c-17707               14095   18.0x     2092.7   19.7x       7.37
pypy-c-17707-lo            19102   24.4x     1354.7   30.4x       6.40
pypy-c-17707-lo-range      18786   24.0x     2800.8   14.7x       6.40
pypy-c-17707-range         13980   17.8x     2899.9   14.2x       7.38
pypy-c-17743               13944   17.8x     2800.3   14.7x       7.30
pypy-c-17761-samuele       13243   16.9x     2983.3   13.8x       7.69
pypy-c-17794-ref-crash     41088   52.4x     1084.5   37.9x      14.62
pypy-c-17950               12888   16.4x     3203.0   12.8x       5.49
pypy-c-18236                9263   11.8x     3702.8   11.1x       5.12
python 2.4.1                 783    1.0x    41150.3    1.0x       0.96

Defaults are: --gc=boehm
'lo' indicates --lowmem
STarting with rev. 18236, gc_pypy.dll is used
"""

import os, sys, pickle, md5
try:
    from subprocess import *
except ImportError:
    Popen = None

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'

def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        raise ValueError, 'this is no valid output: %r' % txt
    return float(line.split()[len(pattern.split())])

def run_cmd(cmd):
    print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    result = pipe.read()
    print "done"
    return result

def run_cmd_subprocess(cmd):
    print "running", cmd
    result = Popen(cmd, stdout=PIPE, creationflags=CREATIONFLAGS
                   ).communicate()[0]
    print "done"
    return result

CREATIONFLAGS = 0
if Popen:
    run_cmd = run_cmd_subprocess
    try:
        import win32con, win32api
    except ImportError:
        pass
    else:
        if USE_HIGH_PRIORITY:
            CREATIONFLAGS = win32con.HIGH_PRIORITY_CLASS
            print "configured to run under high priority"

BENCH_EXECONFIG = '_bench_windows_exe.txt'
bench_exe = None

def reference(progname):
    global bench_exe
    if not bench_exe:
        if os.path.exists(BENCH_EXECONFIG):
            progname = file(BENCH_EXECONFIG).read().strip()
            print "using %s instead of the system default" % progname
        bench_exe = progname
    return bench_exe

def run_version_size(executable=reference('python'), *args):
    ver, size, dll = run_cmd('%s -c "import sys, os; print sys.version.split()[0], '
                             'os.path.getsize(sys.executable), sys.dllhandle"'
                             % executable).split()
    size = int(size)
    try:
        import win32api
    except ImportError:
        pass
    else:
        size += os.path.getsize(win32api.GetModuleFileName(int(dll)))
    return ver, size

def run_pystone(executable=reference('python'), n=0, rpy=False):
    if rpy:
        txt = run_cmd('%s pystone' % executable)
    else:
        argstr = PYSTONE_CMD % (str(n) and n or '')
        txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, PYSTONE_PATTERN)
    print res
    return res

def run_richards(executable=reference('python'), n=20, rpy=False):
    if rpy:
        txt = run_cmd('%s richards' % executable)
    else:
        argstr = RICHARDS_CMD % n
        txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, RICHARDS_PATTERN)
    print res
    return res

def get_executables():
    exes = [name for name in os.listdir('.') if name.endswith('.exe')]
    exes.sort()
    return exes

STAT_FILE = '_bench_windows.dump'
def load_stats(statfile=STAT_FILE):
    try:
        dic = pickle.load(file(statfile, 'rb'))
    except IOError:
        dic = {}
    return dic

def save_stats(dic, statfile=STAT_FILE):
    pickle.dump(dic, file(statfile, 'wb'))

HEADLINE = '''\
executable                  richards           pystone            size (MB)'''
FMT = '''\
%-27s'''             +    '%5d  %5.1fx' +  '  %9.1f  %5.1fx       %5.3f'
FMT2 = '''\
%-27s'''             +  '%5.3f  %5.1f/' +  '  %9.1f  %5.1f/       %5.3f'

def main():
    print 'getting the richards reference'
    ref_rich = run_richards()
    print 'getting the pystone reference'
    ref_stone = run_pystone()
    resdic = {}
    prior = load_stats()
    for exe in get_executables():
        exename = os.path.splitext(exe)[0]
        mtime = os.path.getmtime(exe)
        size = os.path.getsize(exe)
        rpy = size < 500000
        key = md5.new(file(exe,'rb').read()).digest()
        if key in prior:
            print 'skipped', exename
            resdic[key] = prior[key][:2] + (exename, mtime, size)
        else:
            resdic[key] = (run_richards(exe, 2,rpy), run_pystone(exe, 20000, rpy),
                           exename, mtime, size)
            prior[key] = resdic[key] # save result, temporarily
            save_stats(prior)
    save_stats(resdic) # save cleaned result
    res = [ (stone / rich, exe, size, rich, stone)
            for rich, stone, exe, mtime, size in resdic.values()]
    version, size = run_version_size()
    res.append( (ref_stone/ref_rich, 'python %s' % version, size, ref_rich, ref_stone) )
    res.sort()
    print HEADLINE
    for speed2, exe, size, rich, stone in res:
        if speed2 <= ref_stone/ref_rich:
            print FMT % (exe, rich, rich / ref_rich, stone, ref_stone / stone,
                         size / float(1024 * 1024))
        else:
            print FMT2 % (exe, rich, ref_rich / rich, stone, stone / ref_stone,
                          size / float(1024 * 1024))

if __name__ == '__main__':
    main()
