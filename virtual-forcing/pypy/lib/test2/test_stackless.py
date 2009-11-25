from pypy.conftest import gettestobjspace, option

class AppTest_Stackless:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space
        # cannot test the unpickle part on top of py.py
        cls.w_can_unpickle = space.wrap(bool(option.runappdirect))

    def test_pickle(self):
        import new, sys

        mod = new.module('mod')
        sys.modules['mod'] = mod
        mod.can_unpickle = self.can_unpickle
        mod.skip = skip
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
if not can_unpickle:
    skip("cannot test the unpickling part on top of py.py")
print "now running the clone"
tt = pickle.loads(blob)
tt.insert()
seen = []
stackless.run()
assert seen == range(lev, 0, -1)
''' in mod.__dict__
        finally:
            del sys.modules['mod']
