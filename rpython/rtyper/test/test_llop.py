import struct
from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem.rstr import STR
from rpython.rtyper.annlowlevel import llstr
from rpython.rlib.rarithmetic import r_singlefloat

def str_offset():
    base_ofs = (llmemory.offsetof(STR, 'chars') +
                llmemory.itemoffsetof(STR.chars, 0))
    scale_factor = llmemory.sizeof(lltype.Char)
    return base_ofs, scale_factor

class BaseLLOpTest(object):
    
    def test_gc_load_indexed(self):
        buf = struct.pack('dfi', 123.456, 123.456, 0x12345678)
        val = self.gc_load_from_string(rffi.DOUBLE, buf, 0)
        assert val == 123.456
        #
        val = self.gc_load_from_string(rffi.FLOAT, buf, 8)
        assert val == r_singlefloat(123.456)
        #
        val = self.gc_load_from_string(rffi.INT, buf, 12)
        assert val == 0x12345678


class TestDirect(BaseLLOpTest):

    def gc_load_from_string(self, TYPE, buf, offset):
        base_ofs, scale_factor = str_offset()
        lls = llstr(buf)
        return llop.gc_load_indexed(TYPE, lls, offset,
                                    scale_factor, base_ofs)


class TestRTyping(BaseLLOpTest, BaseRtypingTest):

    def gc_load_from_string(self, TYPE, buf, offset):
        def fn(offset):
            lls = llstr(buf)
            base_ofs, scale_factor = str_offset()
            return llop.gc_load_indexed(TYPE, lls, offset,
                                        scale_factor, base_ofs)
        return self.interpret(fn, [offset])
