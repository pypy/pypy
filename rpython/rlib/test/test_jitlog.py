import py
from rpython.jit.tool.oparser import pure_parse
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.backend.model import AbstractCPU
from rpython.jit.metainterp.history import ConstInt, ConstPtr
from rpython.rlib.jitlog import (encode_str, encode_le_16bit, encode_le_64bit)
from rpython.rlib import jitlog as jl

class FakeLog(object):
    def __init__(self):
        self.values = []

    def _write_marked(self, id, text):
        self.values.append(chr(id) + text)

def _get_location(greenkey_list):
    assert len(greenkey_list) == 0
    return '/home/pypy/jit.py', 0, 'enclosed', 99, 'DEL'

class TestLogger(object):

    def make_metainterp_sd(self):
        class FakeJitDriver(object):
            class warmstate(object):
                get_location_types = [jl.MP_FILENAME,jl.MP_INT,jl.MP_SCOPE, jl.MP_INT, jl.MP_OPCODE]
                @staticmethod
                def get_location(greenkey_list):
                    return [jl.wrap(jl.MP_FILENAME[0],'s','/home/pypy/jit.py'),
                            jl.wrap(jl.MP_INT[0], 'i', 0),
                            jl.wrap(jl.MP_SCOPE[0], 's', 'enclosed'),
                            jl.wrap(jl.MP_INT[0], 'i', 99),
                            jl.wrap(jl.MP_OPCODE[0], 's', 'DEL')
                           ]


        class FakeMetaInterpSd:
            cpu = AbstractCPU()
            cpu.ts = None
            jitdrivers_sd = [FakeJitDriver()]
            def get_name_from_address(self, addr):
                return 'Name'
        return FakeMetaInterpSd()

    def test_debug_merge_point(self, tmpdir):
        logger = jl.VMProfJitLogger()
        file = tmpdir.join('binary_file')
        file.ensure()
        fd = file.open('wb')
        logger.cintf.jitlog_init(fd.fileno())
        logger.start_new_trace()
        log_trace = logger.log_trace(jl.MARK_TRACE, self.make_metainterp_sd(), None)
        op = ResOperation(rop.DEBUG_MERGE_POINT, [ConstInt(0), ConstInt(0), ConstInt(0)])
        log_trace.write([], [op])
        #the next line will close 'fd'
        fd.close()
        logger.finish()
        binary = file.read()
        assert binary == chr(jl.MARK_START_TRACE) + jl.encode_le_addr(0) + \
                         jl.encode_str('loop') + jl.encode_le_addr(0) + \
                         chr(jl.MARK_TRACE) + jl.encode_le_addr(0) + \
                         chr(jl.MARK_INPUT_ARGS) + jl.encode_str('') + \
                         chr(jl.MARK_INIT_MERGE_POINT) + b'\x01s\x00i\x08s\x00i\x10s' + \
                         chr(jl.MARK_MERGE_POINT) + \
                         b'\xff' + encode_str('/home/pypy/jit.py') + \
                         b'\x00' + encode_le_64bit(0) + \
                         b'\xff' + encode_str('enclosed') + \
                         b'\x00' + encode_le_64bit(99) + \
                         b'\xff' + encode_str('DEL')

    def test_common_prefix(self):
        fakelog = FakeLog()
        compressor = jl.PrefixCompressor(1)
        # nothing to compress yet!
        result = jl.encode_merge_point(fakelog, compressor, [jl.StringValue(0x0,'s','hello')])
        assert result == b"\xff\x05\x00\x00\x00hello"
        assert fakelog.values == []
        #
        result = jl.encode_merge_point(fakelog, compressor, [jl.StringValue(0x0,'s','hello')])
        assert result == b"\xef"
        assert fakelog.values == ["\x25\x00\x05\x00\x00\x00hello"]
        #
        fakelog.values = []
        result = jl.encode_merge_point(fakelog, compressor, [jl.StringValue(0x0,'s','heiter')])
        assert result == b"\x00\x04\x00\x00\x00iter"
        assert fakelog.values == ["\x25\x00\x02\x00\x00\x00he"]
        #
        fakelog.values = []
        result = jl.encode_merge_point(fakelog, compressor, [jl.StringValue(0x0,'s','heute')])
        assert result == b"\x00\x03\x00\x00\x00ute"
        assert fakelog.values == []
        #
        fakelog.values = []
        result = jl.encode_merge_point(fakelog, compressor, [jl.StringValue(0x0,'s','welt')])
        assert result == b"\xff\x04\x00\x00\x00welt"
        assert fakelog.values == []
        #
        fakelog.values = []
        result = jl.encode_merge_point(fakelog, compressor, [jl.StringValue(0x0,'s','welle')])
        assert result == b"\x00\x02\x00\x00\x00le"
        assert fakelog.values == ["\x25\x00\x03\x00\x00\x00wel"]

    def test_common_prefix_func(self):
        assert jl.commonprefix("","") == ""
        assert jl.commonprefix("/hello/world","/path/to") == "/"
        assert jl.commonprefix("pyramid","python") == "py"
        assert jl.commonprefix("0"*100,"0"*100) == "0"*100
        with py.test.raises(AssertionError):
            jl.commonprefix(None,None)

