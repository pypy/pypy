
from pypy.rpython.rbuilder import AbstractStringBuilderRepr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rstr import string_repr, char_repr,\
     unicode_repr, unichar_repr

MAX = 16*1024*1024

class BaseBuilderRepr(AbstractStringBuilderRepr):
    @classmethod
    def ll_new(cls, init_size):
        if init_size < 0 or init_size > MAX:
            init_size = MAX
        return ootype.new(cls.lowleveltype)

    @staticmethod
    def ll_append_char(builder, char):
        builder.ll_append_char(char)

    @staticmethod
    def ll_append(builder, string):
        builder.ll_append(string)

    @staticmethod
    def ll_append_slice(builder, string, start, end):
        # XXX not sure how to optimize it
        for i in range(start, end):
            builder.ll_append_char(string.ll_stritem_nonneg(i))

    @staticmethod
    def ll_append_multiple_char(builder, char, times):
        for i in range(times):
            builder.ll_append_char(char)

    @staticmethod
    def ll_build(builder):
        return builder.ll_build()

class StringBuilderRepr(BaseBuilderRepr):
    lowleveltype = ootype.StringBuilder
    string_repr = string_repr
    char_repr = char_repr

class UnicodeBuilderRepr(BaseBuilderRepr):
    lowleveltype = ootype.UnicodeBuilder
    string_repr = unicode_repr
    char_repr = unichar_repr

stringbuilder_repr = StringBuilderRepr()
unicodebuilder_repr = UnicodeBuilderRepr()
