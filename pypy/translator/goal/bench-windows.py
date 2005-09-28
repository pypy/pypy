# benchmarks on a windows machine.
# to be executed in the goal folder,
# where a couple of .exe files is expected.

USE_HIGH_PRIORITY = True
# usage with high priority:
# the program will try to import subprocess.
# you can have this with python older than 2.4: copy
# subprocess into lib and change line 392 to use win32

current_result = """
executable                  a.rich   a.stone   r.rich   r.stone   size
pypy-c-17439-hi             37413      678.4   48.2     61.6      5.65
pypy-c-17600-lo             26352      906.2   33.9     46.1      6.43
pypy-c-17634-lo             20108     1023.5   25.9     40.9      6.42
pypy-c-17649-lo             22612     1042.0   29.1     40.1      6.41
pypy-c-17674-lo             19248     1358.8   24.8     30.8      6.40
pypy-c-17674-hi             12402     1941.4   16.0     21.5      7.37
pypy-c-17439-lo             29638      971.4   38.1     43.0      6.49
pypy-c-17707-hi             14095     2092.7   18.1     20.0      7.37
pypy-c-17707-lo             19102     1354.7   24.6     30.9      6.40
pypy-c-17707-lo-range       18786     2800.8   24.2     14.9      6.40
pypy-c-17707-hi-range       13980     2899.9   18.0     14.4      7.38
pypy-c-17743-hi             13944     2800.3   17.9     14.9      7.30
pypy-c-17761-hi-samuele     13243     2983.3   17.0     14.0      7.69
python 2.5a0                  777    41812.1    1.0      1.0      0.96

This new version also shows the size of the plain executable.
Samuele's locality patch now has a nice impact of over 5 percent.
I had even expected a bit more, but fine, yeah!
"""

import os, sys, pickle, md5
try:
    from subprocess import *
except ImportError:
    Popen = None

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

BENCH_EXECONFIG = 'bench_windows_exe.txt'
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

def run_pystone(executable=reference('python'), n=0):
    argstr = PYSTONE_CMD % (str(n) and n or '')
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, PYSTONE_PATTERN)
    print res
    return res

def run_richards(executable=reference('python'), n=20):
    argstr = RICHARDS_CMD % n
    txt = run_cmd('%s -c "%s"' % (executable, argstr))
    res = get_result(txt, RICHARDS_PATTERN)
    print res
    return res

def get_executables():
    exes = [name for name in os.listdir('.') if name.endswith('.exe')]
    exes.sort()
    return exes

STAT_FILE = 'bench_windows.dump'
def load_stats(statfile=STAT_FILE):
    try:
        dic = pickle.load(file(statfile, 'rb'))
    except IOError:
        dic = {}
    return dic

def save_stats(dic, statfile=STAT_FILE):
    pickle.dump(dic, file(statfile, 'wb'))

HEADLINE = '''\
executable                  a.rich   a.stone   r.rich   r.stone   size'''
FMT = '''\
%-27s '''               +  '%5d    %7.1f  ' + '%5.1f    %5.1f     %5.2f'

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
        key = md5.new(file(exe,'rb').read()).digest()
        if key in prior:
            print 'skipped', exename
            resdic[key] = prior[key][:2] + (exename, mtime, size)
        else:
            resdic[key] = (run_richards(exe, 2), run_pystone(exe, 20000),
                           exename, mtime, size)
            prior[key] = resdic[key] # save result, temporarily
            save_stats(prior)
    save_stats(resdic) # save cleaned result
    res = [ (mtime, exe, size, rich, stone)
            for rich, stone, exe, mtime, size in resdic.values()]
    version, size = run_version_size()
    res.append( (9e9, 'python %s' % version, size, ref_rich, ref_stone) )
    res.sort()
    print HEADLINE
    for mtime, exe, size, rich, stone in res:
        print FMT % (exe, rich, stone, rich / ref_rich, ref_stone / stone,
                     size / float(1024 * 1024))

if __name__ == '__main__':
    main()
