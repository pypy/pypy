import time, os, sys
sys.path.insert(0, '/home/arigo/pyjitpl5/lib-python')
sys.path.insert(1, '/home/arigo/pyjitpl5/lib-python/modified-2.5.2')
sys.path.insert(2, '/home/arigo/pyjitpl5/lib-python/2.5.2')
from conftest import testmap

EXECUTABLE = './testing_1'

SKIPS = {'test_popen': 'sys.executable is bogus',
         'test_popen2': 'confused by debugging output of subprocess',
         'test_scope': 'expects an object to be freed',
         'test_strftime': 'incomplete time module in ./testing_1',
         'test_strptime': 'incomplete time module in ./testing_1',
         'test_struct': 'incomplete struct module in ./testing_1',
         'test_xmlrpc': 'incomplete time module in ./testing_1',
        }

names = [os.path.splitext(test.basename)[0]
            for test in testmap
                if not test.skip]
if len(sys.argv) > 1:
    start_at = sys.argv[1]
    del names[:names.index(start_at)]
    print names

assert os.path.isdir('result/')

# ___________________________________________________________

for name in names:
    print >> sys.stderr, name + '...',
    if name in SKIPS:
        print >> sys.stderr, 'skip:', SKIPS[name]
        continue
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
    i = -1
    while (lines[i].startswith('leaving with Return:') or
           lines[i].startswith('TOTAL:') or
           lines[i].startswith('Tracing:') or
           lines[i].startswith('Backend:') or
           lines[i].startswith('Running asm:') or
           lines[i].startswith('Blackhole:')):
        i -= 1
    if '---ending 2---' in lines[i]:
        print >> sys.stderr, 'ok'
    elif (lines[i].startswith('ImportError:') or
          lines[i].startswith('TestSkipped:') or
          lines[i].startswith('ResourceDenied:')):
        print >> sys.stderr, lines[i].rstrip()
    else:
        print >> sys.stderr, "failed!  The last line of the output is:"
        print >> sys.stderr, lines[i].rstrip()
        break
    #time.sleep(1)
