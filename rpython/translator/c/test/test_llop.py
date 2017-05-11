from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.test.test_llop import BaseLLOpTest, str_gc_load
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
                x = str_gc_load(TYPE, buf, offset)
                return lltype.cast_primitive(TARGET_TYPE, x)

            fn = compile(llf, [str, int])
            self.cache[TYPE] = fn
        #
        fn = self.cache[TYPE]
        x = fn(buf, offset)
        return lltype.cast_primitive(TYPE, x)
