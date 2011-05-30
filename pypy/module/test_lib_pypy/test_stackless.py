from pypy.conftest import gettestobjspace, option

class AppTest_Stackless:

    def setup_class(cls):
        import py.test
        py.test.importorskip('greenlet')
        space = gettestobjspace(usemodules=('_stackless', '_socket'))
        cls.space = space
        # cannot test the unpickle part on top of py.py

    def test_pickle(self):
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
import pickle, sys
import stackless
lev = 14

ch = stackless.channel()
seen = []

def recurs(depth, level=1):
    print 'enter level %s%d' % (level*'  ', level)
    seen.append(level)
    if level >= depth:
        ch.send('hi')
    if level < depth:
        recurs(depth, level+1)
    seen.append(level)
    print 'leave level %s%d' % (level*'  ', level)

def demo(depth):
    t = stackless.tasklet(recurs)(depth)
    print ch.receive()
    global blob
    blob = pickle.dumps(t)
    
t = stackless.tasklet(demo)(lev)
stackless.run()
assert seen == range(1, lev+1) + range(lev, 0, -1)
print "now running the clone"
tt = pickle.loads(blob)
tt.insert()
seen = []
stackless.run()
assert seen == range(lev, 0, -1)
''' in mod.__dict__
        finally:
            del sys.modules['mod']
    
    def test_pickle2(self):
        # To test a bug where too much stuff gets pickled when
        # a tasklet halted on stackless.schedule() is pickled.
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        try:
            exec '''
import pickle, sys
import stackless
import socket

def task_should_be_picklable():
    stackless.schedule()

def task_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    stackless.schedule()

def task_pickle(ref_task):
    p = pickle.dumps(ref_task)
    
ref_task = stackless.tasklet(task_should_be_picklable)()
stackless.tasklet(task_socket)()
stackless.tasklet(task_pickle)(ref_task)
stackless.run()
''' in mod.__dict__
        finally:
            del sys.modules['mod']
