import sys
from pypy.rlib import debug
from pypy.jit.tool.oparser import pure_parse
from pypy.jit.metainterp import logger
from pypy.jit.metainterp.typesystem import llhelper
from StringIO import StringIO
from pypy.jit.metainterp.test.test_optimizeopt import equaloplists
from pypy.jit.metainterp.history import AbstractDescr, LoopToken, BasicFailDescr
from pypy.jit.backend.model import AbstractCPU


class Descr(AbstractDescr):
    pass

def capturing(func, *args, **kwds):
    log_stream = StringIO()
    class MyDebugLog:
        def debug_print(self, *args):
            for arg in args:
                print >> log_stream, arg,
            print >> log_stream
        def debug_start(self, *args):
            pass
        def debug_stop(self, *args):
            pass
    try:
        debug._log = MyDebugLog()
        func(*args, **kwds)
    finally:
        debug._log = None
    return log_stream.getvalue()

class Logger(logger.Logger):
    def log_loop(self, loop, namespace={}, ops_offset=None):
        self.namespace = namespace
        return capturing(logger.Logger.log_loop, self,
                         loop.inputargs, loop.operations, ops_offset=ops_offset)

    def _make_log_operations(self1):
        class LogOperations(logger.LogOperations):
            def repr_of_descr(self, descr):
                for k, v in self1.namespace.items():
                    if v == descr:
                        return k
                return descr.repr_of_descr()
        logops = LogOperations(self1.metainterp_sd, self1.guard_number)
        self1.logops = logops
        return logops

class TestLogger(object):
    ts = llhelper

    def make_metainterp_sd(self):
        class FakeJitDriver(object):
            class warmstate(object):
                get_location_str = staticmethod(lambda args: "dupa")
        
        class FakeMetaInterpSd:
            cpu = AbstractCPU()
            cpu.ts = self.ts
            jitdrivers_sd = [FakeJitDriver()]
            def get_name_from_address(self, addr):
                return 'Name'
        return FakeMetaInterpSd()

    def reparse(self, inp, namespace=None, check_equal=True):
        """ parse loop once, then log it and parse again.
        Checks that we get the same thing.
        """
        if namespace is None:
            namespace = {}
        loop = pure_parse(inp, namespace=namespace)
        logger = Logger(self.make_metainterp_sd())
        output = logger.log_loop(loop, namespace)
        oloop = pure_parse(output, namespace=namespace)
        if check_equal:
            equaloplists(loop.operations, oloop.operations)
            assert oloop.inputargs == loop.inputargs
        return logger, loop, oloop
    
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

    def test_guard_w_hole(self):
        inp = '''
        [i0]
        i1 = int_add(i0, 1)
        guard_true(i0) [i0, None, i1]
        finish(i1)
        '''
        self.reparse(inp)

    def test_debug_merge_point(self):
        inp = '''
        []
        debug_merge_point(0, 0)
        '''
        _, loop, oloop = self.reparse(inp, check_equal=False)
        assert loop.operations[0].getarg(1).getint() == 0
        assert oloop.operations[0].getarg(1)._get_str() == "dupa"
        
    def test_floats(self):
        inp = '''
        [f0]
        f1 = float_add(3.5, f0)
        '''
        _, loop, oloop = self.reparse(inp)
        equaloplists(loop.operations, oloop.operations)

    def test_jump(self):
        namespace = {'target': LoopToken()}
        namespace['target'].number = 3
        inp = '''
        [i0]
        jump(i0, descr=target)
        '''
        loop = pure_parse(inp, namespace=namespace)
        logger = Logger(self.make_metainterp_sd())
        output = logger.log_loop(loop)
        assert output.splitlines()[-1] == "jump(i0, descr=<Loop3>)"
        pure_parse(output)
        
    def test_guard_descr(self):
        namespace = {'fdescr': BasicFailDescr()}
        inp = '''
        [i0]
        guard_true(i0, descr=fdescr) [i0]
        '''
        loop = pure_parse(inp, namespace=namespace)
        logger = Logger(self.make_metainterp_sd(), guard_number=True)
        output = logger.log_loop(loop)
        assert output.splitlines()[-1] == "guard_true(i0, descr=<Guard0>) [i0]"
        pure_parse(output)
        
        logger = Logger(self.make_metainterp_sd(), guard_number=False)
        output = logger.log_loop(loop)
        lastline = output.splitlines()[-1]
        assert lastline.startswith("guard_true(i0, descr=<")
        assert not lastline.startswith("guard_true(i0, descr=<Guard")

    def test_class_name(self):
        from pypy.rpython.lltypesystem import lltype
        AbcVTable = lltype.Struct('AbcVTable')
        abcvtable = lltype.malloc(AbcVTable, immortal=True)
        namespace = {'Name': abcvtable}
        inp = '''
        [i0]
        p = new_with_vtable(ConstClass(Name))
        '''
        loop = pure_parse(inp, namespace=namespace)
        logger = Logger(self.make_metainterp_sd())
        output = logger.log_loop(loop)
        assert output.splitlines()[-1].endswith(
            " = new_with_vtable(ConstClass(Name))")
        pure_parse(output, namespace=namespace)

    def test_intro_loop(self):
        bare_logger = logger.Logger(self.make_metainterp_sd())
        output = capturing(bare_logger.log_loop, [], [], 1, "foo")
        assert output.splitlines()[0] == "# Loop 1 : foo with 0 ops"
        pure_parse(output)

    def test_intro_bridge(self):
        bare_logger = logger.Logger(self.make_metainterp_sd())
        output = capturing(bare_logger.log_bridge, [], [], 3)
        assert output.splitlines()[0] == "# bridge out of Guard 3 with 0 ops"
        pure_parse(output)

    def test_repr_single_op(self):
        inp = '''
        [i0, i1, i2, p3, p4, p5]
        i6 = int_add(i1, i2)
        i8 = int_add(i6, 3)
        jump(i0, i8, i6, p3, p4, p5)
        '''
        logger, loop, _ = self.reparse(inp)
        op = loop.operations[1]
        assert logger.logops.repr_of_resop(op) == "i8 = int_add(i6, 3)"

    def test_ops_offset(self):
        inp = '''
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_mul(i1, 2)
        jump(i2)
        '''
        loop = pure_parse(inp)
        ops = loop.operations
        ops_offset = {
            ops[0]: 10,
            ops[2]: 30,
            None: 40
            }
        logger = Logger(self.make_metainterp_sd())
        output = logger.log_loop(loop, ops_offset=ops_offset)
        assert output.strip() == """
[i0]
+10: i2 = int_add(i0, 1)
i4 = int_mul(i2, 2)
+30: jump(i4)
+40: --end of the loop--
""".strip()
