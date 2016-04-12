from rpython.jit.tool.oparser import pure_parse
from rpython.jit.metainterp import jitlog
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
                def get_location_str(ptr):
                    if ptr.value == 0:
                        return 'string #3 BYTE_CODE'

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
        assert binary.endswith(b'\x24\x06\x00\x00\x00string\x00\x00\x00\x00\x00\x00\x00\x00')



