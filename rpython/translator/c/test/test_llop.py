from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import llstr
from rpython.rtyper.test.test_llop import BaseLLOpTest, str_offset
from rpython.translator.c.test.test_genc import compile


class TestLLOp(BaseLLOpTest):
    cache = {}

    def gc_load_from_string(self, TYPE, buf, offset):
        if TYPE not in self.cache:
            assert isinstance(TYPE, lltype.Primitive)
            if TYPE in (lltype.Float, lltype.SingleFloat):
                TARGET_TYPE = lltype.Float
            else:
                TARGET_TYPE = lltype.Signed

            def llf(buf, offset):
                base_ofs, scale_factor = str_offset()
                lls = llstr(buf)
                x = llop.gc_load_indexed(TYPE, lls, offset,
                                         scale_factor, base_ofs)
                return lltype.cast_primitive(TARGET_TYPE, x)

            fn = compile(llf, [str, int])
            self.cache[TYPE] = fn
        #
        fn = self.cache[TYPE]
        x = fn(buf, offset)
        return lltype.cast_primitive(TYPE, x)
