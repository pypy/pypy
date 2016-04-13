from rpython.jit.tool.oparser import pure_parse
from rpython.jit.metainterp import jitlog
from rpython.jit.metainterp.jitlog import (encode_str, encode_le_16bit,
        encode_le_64bit)
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.backend.model import AbstractCPU
from rpython.jit.metainterp.history import ConstInt, ConstPtr
import tempfile

class TestLogger(object):

    def make_metainterp_sd(self):
        class FakeJitDriver(object):
            class warmstate(object):
                @staticmethod
                def get_location(greenkey_list):
                    assert len(greenkey_list) == 0
                    return '/home/pypy/jit.py', 0, 'enclosed', 99, 'DEL'

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

