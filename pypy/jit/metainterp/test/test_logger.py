
from pypy.jit.metainterp.test.oparser import pure_parse
from pypy.jit.metainterp import logger
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
        logger.Logger.log_loop(self, loop.inputargs, loop.operations)
        return self.log_stream.getvalue()

    def repr_of_descr(self, descr):
        for k, v in self.namespace.items():
            if v == descr:
                return k
        return "???"

class TestLogger(object):
    ts = llhelper

    def reparse(self, inp, namespace=None, check_equal=True):
        """ parse loop once, then log it and parse again.
        Checks that we get the same thing.
        """
        if namespace is None:
            namespace = {}
        loop = pure_parse(inp, namespace=namespace)
        logger = Logger(self.ts)
        output = logger.log_loop(loop, namespace)
        oloop = pure_parse(output, namespace=namespace)
        if check_equal:
            equaloplists(loop.operations, oloop.operations)
            assert oloop.inputargs == loop.inputargs
        return loop, oloop
    
    def test_simple(self):
        inp = '''
        [i0, i1, i2, p3, p4, p5]
        i6 = int_add(i1, i2)
        i8 = int_add(i6, 3)
        jump(i0, i8, i6, p3, p4, p5)
        '''
        self.reparse(inp)

    def test_descr(self):
        inp = '''
        [p0]
        setfield_gc(p0, 3, descr=somedescr)
        '''
        somedescr = Descr()
        self.reparse(inp, namespace=locals())

    def test_guard(self):
        inp = '''
        [i0]
        i1 = int_add(i0, 1)
        guard_true(i0) [i0, i1]
        finish(i1)
        '''
        self.reparse(inp)

    def test_debug_merge_point(self):
        inp = '''
        []
        debug_merge_point("info")
        '''
        loop, oloop = self.reparse(inp, check_equal=False)
        assert loop.operations[0].args[0]._get_str() == 'info'
        assert oloop.operations[0].args[0]._get_str() == 'info'
        
    def test_floats(self):
        inp = '''
        [f0]
        f1 = float_add(3.5, f0)
        '''
        loop, oloop = self.reparse(inp)
        equaloplists(loop.operations, oloop.operations)       

