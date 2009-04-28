import time, os, sys
sys.path.insert(0, '/home/arigo/pyjitpl5/lib-python')
sys.path.insert(1, '/home/arigo/pyjitpl5/lib-python/modified-2.5.2')
sys.path.insert(2, '/home/arigo/pyjitpl5/lib-python/2.5.2')
from conftest import testmap

EXECUTABLE = './testing_1'

names = [os.path.splitext(test.basename)[0]
            for test in testmap
                if test.core and not test.skip]
if len(sys.argv) > 1:
    start_at = sys.argv[1]
    del names[:names.index(start_at)]
    print names

assert os.path.isdir('result/')

# ___________________________________________________________

for name in names:
    print >> sys.stderr, name + '...',
    f = open('pypyjit_demo.py')
    lines = f.readlines()
    f.close()
    assert lines[0].startswith('TESTNAME = ')
    lines[0] = 'TESTNAME = %r\n' % name
    f = open('pypyjit_demo.py', 'w')
    f.writelines(lines)
    f.close()
    os.system("'%s' > result/%s 2>&1" % (EXECUTABLE, name))
    f = open('result/%s' % name)
    f.seek(0, 2)
    start = max(0, f.tell() - 1000)
    f.seek(start)
    lines = f.readlines()
    f.close()
    if '---ending 2---' in lines[-1]:
        print >> sys.stderr, 'ok'
    elif (lines[-1].startswith('ImportError: No module named ') or
          lines[-1].startswith('TestSkipped:')):
        print >> sys.stderr, lines[-1].rstrip()
    else:
        print >> sys.stderr, "failed!  The last line of the output is:"
        print >> sys.stderr, lines[-1].rstrip()
        break
    #time.sleep(1)
