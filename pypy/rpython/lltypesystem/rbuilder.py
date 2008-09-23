
from pypy.rpython.rbuilder import AbstractStringBuilderRepr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rstr import STR, UNICODE, char_repr,\
     string_repr, unichar_repr, unicode_repr
from pypy.rpython.annlowlevel import llstr
from pypy.rlib import rgc
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.lltypesystem.lltype import staticAdtMethod
from pypy.tool.sourcetools import func_with_new_name

GROW_FAST_UNTIL = 100*1024*1024      # 100 MB

def new_grow_func(name):
    def stringbuilder_grow(ll_builder, needed):
        allocated = ll_builder.allocated
        if allocated < GROW_FAST_UNTIL:
            new_allocated = allocated << 1
        else:
            extra_size = allocated >> 2
            try:
                new_allocated = ovfcheck(allocated + extra_size)
            except OverflowError:
                raise MemoryError
        try:
            new_allocated = ovfcheck(new_allocated + needed)
        except OverflowError:
            raise MemoryError
        ll_builder.buf = rgc.resize_buffer(ll_builder.buf, ll_builder.used,
                                           new_allocated)
        ll_builder.allocated = new_allocated
    return func_with_new_name(stringbuilder_grow, name)

stringbuilder_grow = new_grow_func('stringbuilder_grow')
unicodebuilder_grow = new_grow_func('unicodebuilder_grow')

STRINGBUILDER = lltype.GcStruct('stringbuilder',
                              ('allocated', lltype.Signed),
                              ('used', lltype.Signed),
                              ('buf', lltype.Ptr(STR)),
                                adtmeths={'grow':staticAdtMethod(stringbuilder_grow)})

UNICODEBUILDER = lltype.GcStruct('unicodebuilder',
                                 ('allocated', lltype.Signed),
                                 ('used', lltype.Signed),
                                 ('buf', lltype.Ptr(UNICODE)),
                                 adtmeths={'grow':staticAdtMethod(unicodebuilder_grow)})

MAX = 16*1024*1024

class BaseStringBuilderRepr(AbstractStringBuilderRepr):
    @classmethod
    def ll_new(cls, init_size):
        if init_size < 0 or init_size > MAX:
            init_size = MAX
        ll_builder = lltype.malloc(cls.lowleveltype.TO)
        ll_builder.allocated = init_size
        ll_builder.used = 0
        ll_builder.buf = rgc.resizable_buffer_of_shape(cls.basetp, init_size)
        return ll_builder

    @staticmethod
    def ll_append(ll_builder, ll_str):
        used = ll_builder.used
        lgt = len(ll_str.chars)
        needed = lgt + used
        if needed >= ll_builder.allocated:
            ll_builder.grow(ll_builder, lgt)
        ll_str.copy_contents(ll_str, ll_builder.buf, 0, used, lgt)
        ll_builder.used = needed
    
    @staticmethod
    def ll_append_char(ll_builder, char):
        if ll_builder.used == ll_builder.allocated:
            ll_builder.grow(ll_builder, 1)
        ll_builder.buf.chars[ll_builder.used] = char
        ll_builder.used += 1

    @staticmethod
    def ll_append_slice(ll_builder, ll_str, start, end):
        needed = end - start
        used = ll_builder.used
        if needed + used >= ll_builder.allocated:
            ll_builder.grow(ll_builder, needed)
        assert needed >= 0
        ll_str.copy_contents(ll_str, ll_builder.buf, start, used, needed)
        ll_builder.used = needed + used

    @staticmethod
    def ll_append_multiple_char(ll_builder, char, times):
        used = ll_builder.used
        if times + used >= ll_builder.allocated:
            ll_builder.grow(ll_builder, times)
        for i in range(times):
            ll_builder.buf.chars[used] = char
            used += 1
        ll_builder.used = used

    @staticmethod
    def ll_build(ll_builder):
        final_size = ll_builder.used
        return rgc.finish_building_buffer(ll_builder.buf, final_size)

class StringBuilderRepr(BaseStringBuilderRepr):
    lowleveltype = lltype.Ptr(STRINGBUILDER)
    basetp = STR
    string_repr = string_repr
    char_repr = char_repr

class UnicodeBuilderRepr(BaseStringBuilderRepr):
    lowleveltype = lltype.Ptr(UNICODEBUILDER)
    basetp = UNICODE
    string_repr = unicode_repr
    char_repr = unichar_repr

unicodebuilder_repr = UnicodeBuilderRepr()
stringbuilder_repr = StringBuilderRepr()
