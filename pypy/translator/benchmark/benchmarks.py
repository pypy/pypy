import os, sys, time, pickle, re, py

PYSTONE_CMD = 'from test import pystone;pystone.main(%s)'
PYSTONE_PATTERN = 'This machine benchmarks at'
PYSTONE_ASCENDING_GOOD = True

RICHARDS_CMD = 'from richards import *;main(iterations=%d)'
RICHARDS_PATTERN = 'Average time per iteration:'
RICHARDS_ASCENDING_GOOD = False

def get_result(txt, pattern):
    for line in txt.split('\n'):
        if line.startswith(pattern):
            break
    else:
        print repr(txt)
        print 'warning: this is not valid output'
        return 99999.0
    return float(line.split()[len(pattern.split())])

def run_cmd(cmd):
    #print "running", cmd
    pipe = os.popen(cmd + ' 2>&1')
    r = pipe.read()
    status = pipe.close()
    if status:
        print "warning: %r had exit status %s"%(cmd, status)
    return r

def run_pystone(executable='/usr/local/bin/python', n=''):
    distdir = py.magic.autopath().dirpath().dirpath().dirpath().dirpath()
    pystone = distdir.join('lib-python').join('2.4.1').join('test').join('pystone.py')
    txt = run_cmd('"%s" "%s" %s' % (executable, pystone, n))
    return get_result(txt, PYSTONE_PATTERN)

def run_richards(executable='/usr/local/bin/python', n=5):
    richards = py.magic.autopath().dirpath().dirpath().join('goal').join('richards.py')
    txt = run_cmd('"%s" %s %s' % (executable, richards, n))
    return get_result(txt, RICHARDS_PATTERN)

def run_translate(executable='/usr/local/bin/python'):
    translate = py.magic.autopath().dirpath().dirpath().join('goal').join('translate.py')
    argstr = 'sh -c "time %s %s --text --batch --backendopt --no-compile targetrpystonedalone.py > /dev/null 2>/dev/null" 2>&1 | grep real'
    cmd = argstr%(executable, translate)
    txt = run_cmd(cmd)
    m = re.match('real\s+(?P<mins>\\d+)m(?P<secs>\\d+\\.\\d+)s', txt)
    if not m:
       print repr(txt)
       print 'ow'
       return 99999.0
    return 1000*(float(m.group('mins'))*60 + float(m.group('secs')))

BENCHMARKS = [('richards', run_richards, RICHARDS_ASCENDING_GOOD, 'ms'),
              ('pystone', run_pystone, PYSTONE_ASCENDING_GOOD, ''),
              ('translate', run_translate, RICHARDS_ASCENDING_GOOD, 'ms'),
             ]
