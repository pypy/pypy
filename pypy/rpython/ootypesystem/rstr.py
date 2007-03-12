from pypy.rpython.error import TyperError
from pypy.rpython.rstr import AbstractStringRepr,AbstractCharRepr,\
     AbstractUniCharRepr, AbstractStringIteratorRepr,\
     AbstractLLHelpers
from pypy.rpython.rmodel import IntegerRepr
from pypy.rpython.lltypesystem.lltype import Ptr, Char, UniChar
from pypy.rpython.ootypesystem import ootype

# TODO: investigate if it's possible and it's worth to concatenate a
# String and a Char directly without passing to Char-->String
# conversion

class StringRepr(AbstractStringRepr):
    """
    Some comments about the state of ootype strings at the end of Tokyo sprint

    What was accomplished:
    - The rstr module was split in an lltype and ootype version.
    - There is the beginnings of a String type in ootype.
    - The runtime representation of Strings is a subclass of the builtin str.
      The idea is that this saves us from boilerplate code implementing the
      builtin str methods.

    Nothing more was done because of lack of time and paralysis in the face
    of too many problems. Among other things, to write any meaningful tests
    we first need conversion from Chars to Strings (because
    test_llinterp.interpret won't accept strings as arguments). We will need a
    new low-level operation (convert_char_to_oostring or some such) for this.
    """

    lowleveltype = ootype.String

    def __init__(self, *args):
        AbstractStringRepr.__init__(self, *args)
        self.ll = LLHelpers

    def convert_const(self, value):
        if value is None:
            return ootype.String._null
        if not isinstance(value, str):
            raise TyperError("not a str: %r" % (value,))
        return ootype.make_string(value)

    def make_iterator_repr(self):
        return string_iterator_repr

    def _list_length_items(self, hop, v_lst, LIST):
        # ootypesystem list has a different interface that
        # lltypesystem list, so we don't need to calculate the lenght
        # here and to pass the 'items' array. Let's pass the list
        # itself and let LLHelpers.join to manipulate it directly.
        c_length = hop.inputconst(ootype.Void, None)
        return c_length, v_lst


class CharRepr(AbstractCharRepr, StringRepr):
    lowleveltype = Char

class UniCharRepr(AbstractUniCharRepr):
    lowleveltype = UniChar

class LLHelpers(AbstractLLHelpers):

    def ll_chr2str(ch):
        return ootype.oostring(ch, -1)

    def ll_strhash(s):
        return ootype.oohash(s)

    def ll_strfasthash(s):
        return ootype.oohash(s)

    def ll_char_mul(ch, times):
        buf = ootype.new(ootype.StringBuilder)
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
        buf = ootype.new(ootype.StringBuilder)

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
        buf = ootype.new(ootype.StringBuilder)
        length = lst.ll_length()
        buf.ll_allocate(length)
        i = 0
        while i < length:
            buf.ll_append_char(lst.ll_getitem_fast(i))
            i += 1
        return buf.ll_build()

    def ll_join_strs(length_dummy, lst):
        buf = ootype.new(ootype.StringBuilder)
        length = lst.ll_length()
        #buf.ll_allocate(length)
        i = 0
        while i < length:
            buf.ll_append(lst.ll_getitem_fast(i))
            i += 1
        return buf.ll_build()

    def ll_stringslice_startonly(s, start):
        return s.ll_substring(start, s.ll_strlen() - start)

    def ll_stringslice(s, slice):
        start = slice.start
        stop = slice.stop
        length = s.ll_strlen()        
        if stop > length:
            stop = length
        return s.ll_substring(start, stop-start)

    def ll_stringslice_minusone(s):
        return s.ll_substring(0, s.ll_strlen()-1)

    def ll_split_chr(LIST, s, c):
        return s.ll_split_chr(c)

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
        #now get digits
        val = 0
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
string_repr = StringRepr()
char_repr = CharRepr()
unichar_repr = UniCharRepr()
char_repr.ll = LLHelpers
unichar_repr.ll = LLHelpers
emptystr = string_repr.convert_const("")

class StringIteratorRepr(AbstractStringIteratorRepr):
    lowleveltype = ootype.Record({'string': string_repr.lowleveltype,
                                  'index': ootype.Signed})

    def __init__(self):
        self.ll_striter = ll_striter
        self.ll_strnext = ll_strnext

def ll_striter(string):
    iter = ootype.new(string_iterator_repr.lowleveltype)
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

string_iterator_repr = StringIteratorRepr()


# these should be in rclass, but circular imports prevent (also it's
# not that insane that a string constant is built in this file).

instance_str_prefix = string_repr.convert_const("<")
instance_str_suffix = string_repr.convert_const(" object>")

unboxed_instance_str_prefix = string_repr.convert_const("<unboxed ")
unboxed_instance_str_suffix = string_repr.convert_const(">")

list_str_open_bracket = string_repr.convert_const("[")
list_str_close_bracket = string_repr.convert_const("]")
list_str_sep = string_repr.convert_const(", ")
