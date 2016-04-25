import py
from rpython.jit.tool.oparser import pure_parse
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.backend.model import AbstractCPU
from rpython.jit.metainterp.history import ConstInt, ConstPtr
from rpython.rlib.jitlog import (encode_str, encode_le_16bit, encode_le_64bit)
from rpython.rlib import jitlog as jl

class TestLogger(object):

    def make_metainterp_sd(self):
        class FakeJitDriver(object):
            class warmstate(object):
                @staticmethod
                def get_location(greenkey_list):
                    assert len(greenkey_list) == 0
                    return '/home/pypy/jit.py', 0, 'enclosed', 99, 'DEL'
                get_location_types = [(jl.MP_FILENAME,'s'),(0x0,'i'),(jl.MP_SCOPE,'s'), (0x0,'i'), (jl.MP_OPCODE, 's')]

        class FakeMetaInterpSd:
            cpu = AbstractCPU()
            cpu.ts = None
            jitdrivers_sd = [FakeJitDriver()]
            def get_name_from_address(self, addr):
                return 'Name'
        return FakeMetaInterpSd()

    def test_debug_merge_point(self, tmpdir):
        logger = jitlog.VMProfJitLogger()
        file = tmpdir.join('binary_file')
        file.ensure()
        fd = file.open('wb')
        logger.cintf.jitlog_init(fd.fileno())
        log_trace = logger.log_trace(0, self.make_metainterp_sd(), None)
        op = ResOperation(rop.DEBUG_MERGE_POINT, [ConstInt(0), ConstInt(0), ConstInt(0)])
        log_trace.write([], [op])
        #the next line will close 'fd'
        fd.close()
        logger.finish()
        binary = file.read()
        assert binary.startswith(b'\x00\x04\x00\x00\x00loop')
        assert binary.endswith(b'\x24' + \
                               encode_str('/home/pypy/jit.py') + \
                               encode_le_16bit(0) + \
                               encode_str('enclosed') + \
                               encode_le_64bit(99) + \
                               encode_str('DEL'))

    class FakeLog(object):
        def _write_marked(self, id, text):
            pass

    def test_common_prefix(self):
        fakelog = FakeLog()
        logger = jitlog.LogTrace(0x0, {}, None, None, fakelog)

    def test_common_prefix_func(self):
        assert jl.commonprefix("","") == ""
        assert jl.commonprefix("/hello/world","/path/to") == "/"
        assert jl.commonprefix("pyramid","python") == "py"
        assert jl.commonprefix("0"*100,"0"*100) == "0"*100
        with py.test.raises(AssertionError):
            jl.commonprefix(None,None)

