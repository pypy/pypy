
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.backend import logger
from pypy.jit.metainterp.typesystem import llhelper
from StringIO import StringIO
from pypy.jit.metainterp.test.test_optimizeopt import equaloplists
from pypy.jit.metainterp.history import AbstractDescr

class Descr(AbstractDescr):
    pass

class Logger(logger.Logger):
    def log_loop(self, loop, namespace={}):
        self.log_stream = StringIO()
        self.namespace = namespace
        logger.Logger.log_loop(self, loop)
        return self.log_stream.getvalue()

    def repr_of_descr(self, descr):
        for k, v in self.namespace.items():
            if v == descr:
                return k
        return "???"

class TestLogger(object):
    ts = llhelper

    def reparse(self, inp, namespace=None):
        """ parse loop once, then log it and parse again,
        return both
        """
        loop = parse(inp, namespace=namespace)
        logger = Logger(self.ts)
        output = logger.log_loop(loop, namespace)
        oloop = parse(output, namespace=namespace)
        return loop, oloop
    
    def test_simple(self):
        inp = '''
        [i0, i1, i2, p3, p4, p5]
        i6 = int_add(i1, i2)
        i8 = int_add(i6, 3)
        jump(i0, i8, i6, p3, p4, p5)
        '''
        loop, oloop = self.reparse(inp)
        equaloplists(oloop.operations, loop.operations)
        assert oloop.inputargs == loop.inputargs

    def test_descr(self):
        inp = '''
        [p0]
        setfield_gc(p0, 3, descr=somedescr)
        '''
        somedescr = Descr()
        loop, oloop = self.reparse(inp, namespace=locals())
        equaloplists(loop.operations, oloop.operations)

    def test_guard(self):
        inp = '''
        [i0]
        guard_true(i0)
          i1 = int_add(i0, 1)
          guard_true(i1)
             fail(i1)
          fail(i1)
        fail(i0)
        '''
        loop, oloop = self.reparse(inp)
        equaloplists(loop.operations, oloop.operations)

    def test_debug_merge_point(self):
        inp = '''
        []
        debug_merge_point("info")
        '''
        loop, oloop = self.reparse(inp)
        assert oloop.operations[0].args[0]._get_str() == 'info'
        
