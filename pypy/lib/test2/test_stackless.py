from pypy.conftest import gettestobjspace

class AppTest_Stackless:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('_stackless',))
        cls.space = space

    def test_pickle(self):
        import pickle, sys
        import stackless
        
        ch = stackless.channel()
        
        def recurs(depth, level=1):
            print 'enter level %s%d' % (level*'  ', level)
            if level >= depth:
                ch.send('hi')
            if level < depth:
                recurs(depth, level+1)
            print 'leave level %s%d' % (level*'  ', level)
        
        def demo(depth):
            t = stackless.tasklet(recurs)(depth)
            print ch.receive()
            blob = pickle.dumps(t)
        
        t = stackless.tasklet(demo)(14)
        stackless.run()
        
# remark: think of fixing cells etc. on the sprint
