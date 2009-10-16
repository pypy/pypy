from pypy.tool.pairtype import pairtype
from pypy.rpython.error import TyperError
from pypy.rpython.rstr import AbstractStringRepr,AbstractCharRepr,\
     AbstractUniCharRepr, AbstractStringIteratorRepr,\
     AbstractLLHelpers, AbstractUnicodeRepr
from pypy.rpython.rmodel import IntegerRepr
from pypy.rpython.lltypesystem.lltype import Ptr, Char, UniChar, typeOf,\
     cast_primitive
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rmodel import Repr

# TODO: investigate if it's possible and it's worth to concatenate a
# String and a Char directly without passing to Char-->String
# conversion

class BaseOOStringRepr(Repr):

    def __init__(self, *args):
        AbstractStringRepr.__init__(self, *args)
        self.ll = LLHelpers

    def convert_const(self, value):
        if value is None:
            return self.lowleveltype._null
        if not isinstance(value, self.basetype):
            raise TyperError("not a str: %r" % (value,))
        return self.make_string(value)

    def make_string(self, value):
        raise NotImplementedError

    def make_iterator_repr(self):
        return self.string_iterator_repr

    def _list_length_items(self, hop, v_lst, LIST):
        # ootypesystem list has a different interface that
        # lltypesystem list, so we don't need to calculate the lenght
        # here and to pass the 'items' array. Let's pass the list
        # itself and let LLHelpers.join to manipulate it directly.
        c_length = hop.inputconst(ootype.Void, None)
        return c_length, v_lst


class StringRepr(BaseOOStringRepr, AbstractStringRepr):
    lowleveltype = ootype.String
    basetype = str

    def make_string(self, value):
        return ootype.make_string(value)

    def ll_decode_latin1(self, value):
        sb = ootype.new(ootype.UnicodeBuilder)
        length = value.ll_strlen()
        sb.ll_allocate(length)
        for i in range(length):
            c = value.ll_stritem_nonneg(i)
            sb.ll_append_char(cast_primitive(UniChar, c))
        return sb.ll_build()


class UnicodeRepr(BaseOOStringRepr, AbstractUnicodeRepr):
    lowleveltype = ootype.Unicode
    basetype = basestring

    def make_string(self, value):
        return ootype.make_unicode(value)

    def ll_str(self, value):
        sb = ootype.new(ootype.StringBuilder)
        lgt = value.ll_strlen()
        sb.ll_allocate(lgt)
        for i in range(lgt):
            c = value.ll_stritem_nonneg(i)
            if ord(c) > 127:
                raise UnicodeEncodeError("%d > 127, not ascii" % ord(c))
            sb.ll_append_char(cast_primitive(Char, c))
        return sb.ll_build()

    def ll_encode_latin1(self, value):
        sb = ootype.new(ootype.StringBuilder)
        length = value.ll_strlen()
        sb.ll_allocate(length)
        for i in range(length):
            c = value.ll_stritem_nonneg(i)
            if ord(c) > 255:
                raise UnicodeEncodeError("%d > 255, not latin-1" % ord(c))
            sb.ll_append_char(cast_primitive(Char, c))
        return sb.ll_build()

class CharRepr(AbstractCharRepr, StringRepr):
    lowleveltype = Char

class UniCharRepr(AbstractUniCharRepr, UnicodeRepr):
    lowleveltype = UniChar


class __extend__(pairtype(UniCharRepr, UnicodeRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        rstr = llops.rtyper.type_system.rstr
        if r_from == unichar_repr and r_to == unicode_repr:
            return llops.gendirectcall(r_from.ll.ll_unichr2unicode, v)
        return NotImplemented

class LLHelpers(AbstractLLHelpers):

    def ll_chr2str(ch):
        return ootype.oostring(ch, -1)

    def ll_str2unicode(s):
        return ootype.oounicode(s, -1)

    def ll_unichr2unicode(ch):
        return ootype.oounicode(ch, -1)

    def ll_strhash(s):
        return s.ll_hash()

    def ll_strfasthash(s):
        return s.ll_hash()

    def ll_char_mul(ch, times):
        if times < 0:
            times = 0
        if typeOf(ch) == Char:
            buf = ootype.new(ootype.StringBuilder)
        else:
            buf = ootype.new(ootype.UnicodeBuilder)
        buf.ll_allocate(times)
        i = 0
        while i<times:
            buf.ll_append_char(ch)
            i+= 1
        return buf.ll_build()

    def ll_streq(s1, s2):
        if s1 is None:
            return s2 is None
        return s1.ll_streq(s2)

    def ll_strcmp(s1, s2):
        if not s1 and not s2:
            return True
        if not s1 or not s2:
            return False
        return s1.ll_strcmp(s2)

    def ll_join(s, length_dummy, lst):
        length = lst.ll_length()
        buf = ootype.new(typeOf(s).builder)

        # TODO: check if it's worth of preallocating the buffer with
        # the exact length
##        itemslen = 0
##        i = 0
##        while i < length:
##            itemslen += lst.ll_getitem_fast(i).ll_strlen()
##            i += 1
##        resultlen = itemslen + s.ll_strlen()*(length-1)
##        buf.ll_allocate(resultlen)

        i = 0
        while i < length-1:
            item = lst.ll_getitem_fast(i)
            buf.ll_append(item)
            buf.ll_append(s)
            i += 1
        if length > 0:
            lastitem = lst.ll_getitem_fast(i)
            buf.ll_append(lastitem)
        return buf.ll_build()

    def ll_join_chars(length_dummy, lst):
        if typeOf(lst).ITEM == Char:
            buf = ootype.new(ootype.StringBuilder)
        else:
            buf = ootype.new(ootype.UnicodeBuilder)
        length = lst.ll_length()
        buf.ll_allocate(length)
        i = 0
        while i < length:
            buf.ll_append_char(lst.ll_getitem_fast(i))
            i += 1
        return buf.ll_build()

    def ll_join_strs(length_dummy, lst):
        if typeOf(lst).ITEM == ootype.String:
            buf = ootype.new(ootype.StringBuilder)
        else:
            buf = ootype.new(ootype.UnicodeBuilder)
        length = lst.ll_length()
        #buf.ll_allocate(length)
        i = 0
        while i < length:
            buf.ll_append(lst.ll_getitem_fast(i))
            i += 1
        return buf.ll_build()

    def ll_stringslice_startonly(s, start):
        return s.ll_substring(start, s.ll_strlen() - start)

    def ll_stringslice_startstop(s, start, stop):
        length = s.ll_strlen()        
        if stop > length:
            stop = length
        return s.ll_substring(start, stop-start)

    def ll_stringslice_minusone(s):
        return s.ll_substring(0, s.ll_strlen()-1)

    def ll_split_chr(RESULT, s, c):
        return RESULT.ll_convert_from_array(s.ll_split_chr(c))

    def ll_int(s, base):
        if not 2 <= base <= 36:
            raise ValueError
        strlen = s.ll_strlen()
        i = 0
        #XXX: only space is allowed as white space for now
        while i < strlen and s.ll_stritem_nonneg(i) == ' ':
            i += 1
        if not i < strlen:
            raise ValueError
        #check sign
        sign = 1
        if s.ll_stritem_nonneg(i) == '-':
            sign = -1
            i += 1
        elif s.ll_stritem_nonneg(i) == '+':
            i += 1;
        # skip whitespaces between sign and digits
        while i < strlen and s.ll_stritem_nonneg(i) == ' ':
            i += 1
        #now get digits
        val = 0
        oldpos = i
        while i < strlen:
            c = ord(s.ll_stritem_nonneg(i))
            if ord('a') <= c <= ord('z'):
                digit = c - ord('a') + 10
            elif ord('A') <= c <= ord('Z'):
                digit = c - ord('A') + 10
            elif ord('0') <= c <= ord('9'):
                digit = c - ord('0')
            else:
                break
            if digit >= base:
                break
            val = val * base + digit
            i += 1
        if i == oldpos:
            raise ValueError # catch strings like '+' and '+  '
        #skip trailing whitespace
        while i < strlen and s.ll_stritem_nonneg(i) == ' ':
            i += 1
        if not i == strlen:
            raise ValueError
        return sign * val

    def ll_float(ll_str):
        return ootype.ooparse_float(ll_str)
    
    # interface to build strings:
    #   x = ll_build_start(n)
    #   ll_build_push(x, next_string, 0)
    #   ll_build_push(x, next_string, 1)
    #   ...
    #   ll_build_push(x, next_string, n-1)
    #   s = ll_build_finish(x)

    def ll_build_start(parts_count):
        return ootype.new(ootype.StringBuilder)

    def ll_build_push(buf, next_string, index):
        buf.ll_append(next_string)

    def ll_build_finish(buf):
        return buf.ll_build()

    def ll_constant(s):
        return ootype.make_string(s)
    ll_constant._annspecialcase_ = 'specialize:memo'

    def do_stringformat(cls, hop, sourcevarsrepr):
        InstanceRepr = hop.rtyper.type_system.rclass.InstanceRepr
        string_repr = hop.rtyper.type_system.rstr.string_repr
        s_str = hop.args_s[0]
        assert s_str.is_constant()
        s = s_str.const

        c_append = hop.inputconst(ootype.Void, 'll_append')
        c_build = hop.inputconst(ootype.Void, 'll_build')
        cm1 = hop.inputconst(ootype.Signed, -1)
        c8 = hop.inputconst(ootype.Signed, 8)
        c10 = hop.inputconst(ootype.Signed, 10)
        c16 = hop.inputconst(ootype.Signed, 16)
        c_StringBuilder = hop.inputconst(ootype.Void, ootype.StringBuilder)        
        v_buf = hop.genop("new", [c_StringBuilder], resulttype=ootype.StringBuilder)

        things = cls.parse_fmt_string(s)
        argsiter = iter(sourcevarsrepr)
        for thing in things:
            if isinstance(thing, tuple):
                code = thing[0]
                vitem, r_arg = argsiter.next()
                if not hasattr(r_arg, 'll_str'):
                    raise TyperError("ll_str unsupported for: %r" % r_arg)
                if code == 's' or (code == 'r' and isinstance(r_arg, InstanceRepr)):
                    vchunk = hop.gendirectcall(r_arg.ll_str, vitem)
                elif code == 'd':
                    assert isinstance(r_arg, IntegerRepr)
                    vchunk = hop.genop('oostring', [vitem, c10], resulttype=ootype.String)
                elif code == 'f':
                    #assert isinstance(r_arg, FloatRepr)
                    vchunk = hop.gendirectcall(r_arg.ll_str, vitem)
                elif code == 'x':
                    assert isinstance(r_arg, IntegerRepr)
                    vchunk = hop.genop('oostring', [vitem, c16], resulttype=ootype.String)
                elif code == 'o':
                    assert isinstance(r_arg, IntegerRepr)
                    vchunk = hop.genop('oostring', [vitem, c8], resulttype=ootype.String)
                else:
                    raise TyperError, "%%%s is not RPython" % (code, )
            else:
                vchunk = hop.inputconst(string_repr, thing)
            #i = inputconst(Signed, i)
            #hop.genop('setarrayitem', [vtemp, i, vchunk])
            hop.genop('oosend', [c_append, v_buf, vchunk], resulttype=ootype.Void)

        hop.exception_cannot_occur()   # to ignore the ZeroDivisionError of '%'
        return hop.genop('oosend', [c_build, v_buf], resulttype=ootype.String)        
    do_stringformat = classmethod(do_stringformat)


def add_helpers():
    dic = {}
    for name, meth in ootype.String._GENERIC_METHODS.iteritems():
        if name in LLHelpers.__dict__:
            continue
        n_args = len(meth.ARGS)
        args = ', '.join(['arg%d' % i for i in range(n_args)])
        code = """
def %s(obj, %s):
    return obj.%s(%s)
""" % (name, args, name, args)
        exec code in dic
        setattr(LLHelpers, name, staticmethod(dic[name]))

add_helpers()
del add_helpers

do_stringformat = LLHelpers.do_stringformat
char_repr = CharRepr()
unichar_repr = UniCharRepr()
char_repr.ll = LLHelpers
unichar_repr.ll = LLHelpers

string_repr = StringRepr()
StringRepr.repr = string_repr
StringRepr.char_repr = char_repr
emptystr = string_repr.convert_const("")
unicode_repr = UnicodeRepr()
UnicodeRepr.repr = unicode_repr
UnicodeRepr.char_repr = unichar_repr


class StringIteratorRepr(AbstractStringIteratorRepr):
    lowleveltype = ootype.Record({'string': string_repr.lowleveltype,
                                  'index': ootype.Signed})

    def __init__(self):
        self.ll_striter = ll_striter
        self.ll_strnext = ll_strnext

class UnicodeIteratorRepr(AbstractStringIteratorRepr):
    lowleveltype = ootype.Record({'string': unicode_repr.lowleveltype,
                                  'index': ootype.Signed})

    def __init__(self):
        self.ll_striter = ll_unicodeiter
        self.ll_strnext = ll_strnext

def ll_striter(string):
    iter = ootype.new(string_repr.string_iterator_repr.lowleveltype)
    iter.string = string
    iter.index = 0
    return iter

def ll_unicodeiter(string):
    iter = ootype.new(unicode_repr.string_iterator_repr.lowleveltype)
    iter.string = string
    iter.index = 0
    return iter

def ll_strnext(iter):
    string = iter.string    
    index = iter.index
    if index >= string.ll_strlen():
        raise StopIteration
    iter.index = index + 1
    return string.ll_stritem_nonneg(index)


StringRepr.string_iterator_repr = StringIteratorRepr()
UnicodeRepr.string_iterator_repr = UnicodeIteratorRepr()

# these should be in rclass, but circular imports prevent (also it's
# not that insane that a string constant is built in this file).

instance_str_prefix = string_repr.convert_const("<")
instance_str_suffix = string_repr.convert_const(" object>")

unboxed_instance_str_prefix = string_repr.convert_const("<unboxed ")
unboxed_instance_str_suffix = string_repr.convert_const(">")

list_str_open_bracket = string_repr.convert_const("[")
list_str_close_bracket = string_repr.convert_const("]")
list_str_sep = string_repr.convert_const(", ")
