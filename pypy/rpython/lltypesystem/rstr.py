from weakref import WeakValueDictionary
from pypy.tool.pairtype import pairtype
from pypy.rpython.error import TyperError
from pypy.rlib.objectmodel import malloc_zero_filled, we_are_translated
from pypy.rlib.objectmodel import _hash_string, enforceargs
from pypy.rlib.debug import ll_assert
from pypy.rlib.jit import elidable, we_are_jitted, dont_look_inside
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.rmodel import inputconst, IntegerRepr
from pypy.rpython.rstr import AbstractStringRepr,AbstractCharRepr,\
     AbstractUniCharRepr, AbstractStringIteratorRepr,\
     AbstractLLHelpers, AbstractUnicodeRepr
from pypy.rpython.lltypesystem import ll_str
from pypy.rpython.lltypesystem.lltype import \
     GcStruct, Signed, Array, Char, UniChar, Ptr, malloc, \
     Bool, Void, GcArray, nullptr, pyobjectptr, cast_primitive, typeOf,\
     staticAdtMethod, GcForwardReference
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem import llmemory
from pypy.tool.sourcetools import func_with_new_name

# ____________________________________________________________
#
#  Concrete implementation of RPython strings:
#
#    struct str {
#        hash: Signed
#        chars: array of Char
#    }

STR = GcForwardReference()
UNICODE = GcForwardReference()

def new_malloc(TP, name):
    def mallocstr(length):
        ll_assert(length >= 0, "negative string length")
        r = malloc(TP, length)
        if not we_are_translated() or not malloc_zero_filled:
            r.hash = 0
        return r
    mallocstr._annspecialcase_ = 'specialize:semierased'
    return func_with_new_name(mallocstr, name)

mallocstr = new_malloc(STR, 'mallocstr')
mallocunicode = new_malloc(UNICODE, 'mallocunicode')

def emptystrfun():
    return emptystr

def emptyunicodefun():
    return emptyunicode

def _new_copy_contents_fun(TP, CHAR_TP, name):
    def _str_ofs(item):
        return (llmemory.offsetof(TP, 'chars') +
                llmemory.itemoffsetof(TP.chars, 0) +
                llmemory.sizeof(CHAR_TP) * item)

    # It'd be nice to be able to look inside this function.
    @dont_look_inside
    @enforceargs(None, None, int, int, int)
    def copy_string_contents(src, dst, srcstart, dststart, length):
        assert srcstart >= 0
        assert dststart >= 0
        assert length >= 0
        src = llmemory.cast_ptr_to_adr(src) + _str_ofs(srcstart)
        dst = llmemory.cast_ptr_to_adr(dst) + _str_ofs(dststart)
        llmemory.raw_memcopy(src, dst, llmemory.sizeof(CHAR_TP) * length)
    copy_string_contents._always_inline_ = True
    #copy_string_contents.oopspec = (
    #    '%s.copy_contents(src, dst, srcstart, dststart, length)' % name)
    return func_with_new_name(copy_string_contents, 'copy_%s_contents' % name)

copy_string_contents = _new_copy_contents_fun(STR, Char, 'string')
copy_unicode_contents = _new_copy_contents_fun(UNICODE, UniChar, 'unicode')

SIGNED_ARRAY = GcArray(Signed)
CONST_STR_CACHE = WeakValueDictionary()
CONST_UNICODE_CACHE = WeakValueDictionary()

class BaseLLStringRepr(Repr):
    def convert_const(self, value):
        if value is None:
            return nullptr(self.lowleveltype.TO)
        #value = getattr(value, '__self__', value)  # for bound string methods
        if not isinstance(value, self.basetype):
            raise TyperError("not a str: %r" % (value,))
        try:
            return self.CACHE[value]
        except KeyError:
            p = self.malloc(len(value))
            for i in range(len(value)):
                p.chars[i] = cast_primitive(self.base, value[i])
            p.hash = 0
            self.ll.ll_strhash(p)   # precompute the hash
            self.CACHE[value] = p
            return p

    def make_iterator_repr(self):
        return self.iterator_repr

    def can_ll_be_null(self, s_value):
        # XXX unicode
        if self is string_repr:
            return s_value.can_be_none()
        else:
            return True     # for CharRepr/UniCharRepr subclasses,
                            # where NULL is always valid: it is chr(0)


    def _list_length_items(self, hop, v_lst, LIST):
        LIST = LIST.TO
        v_length = hop.gendirectcall(LIST.ll_length, v_lst)
        v_items = hop.gendirectcall(LIST.ll_items, v_lst)
        return v_length, v_items

class StringRepr(BaseLLStringRepr, AbstractStringRepr):
    lowleveltype = Ptr(STR)
    basetype = str
    base = Char
    CACHE = CONST_STR_CACHE

    def __init__(self, *args):
        AbstractStringRepr.__init__(self, *args)
        self.ll = LLHelpers
        self.malloc = mallocstr

    def ll_decode_latin1(self, value):
        lgt = len(value.chars)
        s = mallocunicode(lgt)
        for i in range(lgt):
            s.chars[i] = cast_primitive(UniChar, value.chars[i])
        return s

class UnicodeRepr(BaseLLStringRepr, AbstractUnicodeRepr):
    lowleveltype = Ptr(UNICODE)
    basetype = basestring
    base = UniChar
    CACHE = CONST_UNICODE_CACHE

    def __init__(self, *args):
        AbstractUnicodeRepr.__init__(self, *args)
        self.ll = LLHelpers
        self.malloc = mallocunicode

    @elidable
    def ll_str(self, s):
        # XXX crazy that this is here, but I don't want to break
        #     rmodel logic
        if not s:
            return self.ll.ll_constant('None')
        lgt = len(s.chars)
        result = mallocstr(lgt)
        for i in range(lgt):
            c = s.chars[i]
            if ord(c) > 127:
                raise UnicodeEncodeError("character not in ascii range")
            result.chars[i] = cast_primitive(Char, c)
        return result

    @elidable
    def ll_encode_latin1(self, s):
        length = len(s.chars)
        result = mallocstr(length)
        for i in range(length):
            c = s.chars[i]
            if ord(c) > 255:
                raise UnicodeEncodeError("character not in latin1 range")
            result.chars[i] = cast_primitive(Char, c)
        return result

class CharRepr(AbstractCharRepr, StringRepr):
    lowleveltype = Char

class UniCharRepr(AbstractUniCharRepr, UnicodeRepr):
    lowleveltype = UniChar

class __extend__(pairtype(PyObjRepr, AbstractStringRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        v_len = llops.gencapicall('PyString_Size', [v], resulttype=Signed)
        cstr = inputconst(Void, STR)
        cflags = inputconst(Void, {'flavor': 'gc'})
        v_result = llops.genop('malloc_varsize', [cstr, cflags, v_len],
                               resulttype=Ptr(STR))
        llops.gencapicall('PyString_ToRPyString', [v, v_result])
        string_repr = llops.rtyper.type_system.rstr.string_repr
        v_result = llops.convertvar(v_result, string_repr, r_to)
        return v_result


class __extend__(pairtype(AbstractStringRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        string_repr = llops.rtyper.type_system.rstr.string_repr
        v = llops.convertvar(v, r_from, string_repr)
        cchars = inputconst(Void, "chars")
        # xxx put in table
        return llops.gencapicall(
            'PyString_FromRPyString',
            [v],
            resulttype=pyobj_repr,
            _callable=lambda v: pyobjectptr(''.join(v.chars)))

class __extend__(pairtype(AbstractUnicodeRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        unicode_repr = llops.rtyper.type_system.rstr.unicode_repr
        v = llops.convertvar(v, r_from, unicode_repr)
        cchars = inputconst(Void, "chars")
        # xxx put in table
        return llops.gencapicall(
            'PyUnicode_FromRPyUnicode',
            [v],
            resulttype=pyobj_repr,
            _callable=lambda v: pyobjectptr(u''.join(v.chars)))

# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.
#

def ll_construct_restart_positions(s, l):
    # Construct the array of possible restarting positions
    # T = Array_of_ints [-1..len2]
    # T[-1] = -1 s2.chars[-1] is supposed to be unequal to everything else
    T = malloc( SIGNED_ARRAY, l)
    T[0] = 0
    i = 1
    j = 0
    while i<l:
        if s.chars[i] == s.chars[j]:
            j += 1
            T[i] = j
            i += 1
        elif j>0:
            j = T[j-1]
        else:
            T[i] = 0
            i += 1
            j = 0
    return T


FAST_COUNT = 0
FAST_FIND = 1
FAST_RFIND = 2


from pypy.rlib.rarithmetic import LONG_BIT as BLOOM_WIDTH


def bloom_add(mask, c):
    return mask | (1 << (ord(c) & (BLOOM_WIDTH - 1)))

def bloom(mask, c):
    return mask & (1 << (ord(c) & (BLOOM_WIDTH - 1)))


class LLHelpers(AbstractLLHelpers):
    @elidable
    def ll_str_mul(s, times):
        if times < 0:
            times = 0
        try:
            size = ovfcheck(len(s.chars) * times)
        except OverflowError:
            raise MemoryError
        newstr = s.malloc(size)
        i = 0
        if i < size:
            s.copy_contents(s, newstr, 0, 0, len(s.chars))
            i += len(s.chars)
        while i < size:
            if i <= size - i:
                j = i
            else:
                j = size - i
            s.copy_contents(newstr, newstr, 0, i, j)
            i += j
        return newstr

    @elidable
    def ll_char_mul(ch, times):
        if typeOf(ch) is Char:
            malloc = mallocstr
        else:
            malloc = mallocunicode
        if times < 0:
            times = 0
        newstr = malloc(times)
        j = 0
        # XXX we can use memset here, not sure how useful this is
        while j < times:
            newstr.chars[j] = ch
            j += 1
        return newstr

    def ll_strlen(s):
        return len(s.chars)

    def ll_stritem_nonneg(s, i):
        chars = s.chars
        ll_assert(i>=0, "negative str getitem index")
        ll_assert(i<len(chars), "str getitem index out of bound")
        return chars[i]
    ll_stritem_nonneg._annenforceargs_ = [None, int]

    def ll_chr2str(ch):
        if typeOf(ch) is Char:
            malloc = mallocstr
        else:
            malloc = mallocunicode
        s = malloc(1)
        s.chars[0] = ch
        return s

    def ll_str2unicode(str):
        lgt = len(str.chars)
        s = mallocunicode(lgt)
        for i in range(lgt):
            if ord(str.chars[i]) > 127:
                raise UnicodeDecodeError
            s.chars[i] = cast_primitive(UniChar, str.chars[i])
        return s
    ll_str2unicode.oopspec = 'str.str2unicode(str)'

    @elidable
    def ll_strhash(s):
        # unlike CPython, there is no reason to avoid to return -1
        # but our malloc initializes the memory to zero, so we use zero as the
        # special non-computed-yet value.
        x = s.hash
        if x == 0:
            x = _hash_string(s.chars)
            if x == 0:
                x = 29872897
            s.hash = x
        return x

    def ll_strfasthash(s):
        return s.hash     # assumes that the hash is already computed

    @elidable
    def ll_strconcat(s1, s2):
        len1 = len(s1.chars)
        len2 = len(s2.chars)
        newstr = s1.malloc(len1 + len2)
        s1.copy_contents(s1, newstr, 0, 0, len1)
        s1.copy_contents(s2, newstr, 0, len1, len2)
        return newstr
    ll_strconcat.oopspec = 'stroruni.concat(s1, s2)'

    @elidable
    def ll_strip(s, ch, left, right):
        s_len = len(s.chars)
        if s_len == 0:
            return s.empty()
        lpos = 0
        rpos = s_len - 1
        if left:
            while lpos < rpos and s.chars[lpos] == ch:
                lpos += 1
        if right:
            while lpos < rpos and s.chars[rpos] == ch:
                rpos -= 1
        r_len = rpos - lpos + 1
        result = s.malloc(r_len)
        s.copy_contents(s, result, lpos, 0, r_len)
        return result

    @elidable
    def ll_upper(s):
        s_chars = s.chars
        s_len = len(s_chars)
        if s_len == 0:
            return s.empty()
        i = 0
        result = mallocstr(s_len)
        #        ^^^^^^^^^ specifically to explode on unicode
        while i < s_len:
            ch = s_chars[i]
            if 'a' <= ch <= 'z':
                ch = chr(ord(ch) - 32)
            result.chars[i] = ch
            i += 1
        return result

    @elidable
    def ll_lower(s):
        s_chars = s.chars
        s_len = len(s_chars)
        if s_len == 0:
            return s.empty()
        i = 0
        result = mallocstr(s_len)
        #        ^^^^^^^^^ specifically to explode on unicode
        while i < s_len:
            ch = s_chars[i]
            if 'A' <= ch <= 'Z':
                ch = chr(ord(ch) + 32)
            result.chars[i] = ch
            i += 1
        return result

    def ll_join(s, length, items):
        s_chars = s.chars
        s_len = len(s_chars)
        num_items = length
        if num_items == 0:
            return s.empty()
        itemslen = 0
        i = 0
        while i < num_items:
            itemslen += len(items[i].chars)
            i += 1
        result = s.malloc(itemslen + s_len * (num_items - 1))
        res_index = len(items[0].chars)
        s.copy_contents(items[0], result, 0, 0, res_index)
        i = 1
        while i < num_items:
            s.copy_contents(s, result, 0, res_index, s_len)
            res_index += s_len
            lgt = len(items[i].chars)
            s.copy_contents(items[i], result, 0, res_index, lgt)
            res_index += lgt
            i += 1
        return result

    @elidable
    def ll_strcmp(s1, s2):
        if not s1 and not s2:
            return True
        if not s1 or not s2:
            return False
        chars1 = s1.chars
        chars2 = s2.chars
        len1 = len(chars1)
        len2 = len(chars2)

        if len1 < len2:
            cmplen = len1
        else:
            cmplen = len2
        i = 0
        while i < cmplen:
            diff = ord(chars1[i]) - ord(chars2[i])
            if diff != 0:
                return diff
            i += 1
        return len1 - len2

    @elidable
    def ll_streq(s1, s2):
        if s1 == s2:       # also if both are NULLs
            return True
        if not s1 or not s2:
            return False
        len1 = len(s1.chars)
        len2 = len(s2.chars)
        if len1 != len2:
            return False
        j = 0
        chars1 = s1.chars
        chars2 = s2.chars
        while j < len1:
            if chars1[j] != chars2[j]:
                return False
            j += 1
        return True
    ll_streq.oopspec = 'stroruni.equal(s1, s2)'

    @elidable
    def ll_startswith(s1, s2):
        len1 = len(s1.chars)
        len2 = len(s2.chars)
        if len1 < len2:
            return False
        j = 0
        chars1 = s1.chars
        chars2 = s2.chars
        while j < len2:
            if chars1[j] != chars2[j]:
                return False
            j += 1

        return True

    @elidable
    def ll_endswith(s1, s2):
        len1 = len(s1.chars)
        len2 = len(s2.chars)
        if len1 < len2:
            return False
        j = 0
        chars1 = s1.chars
        chars2 = s2.chars
        offset = len1 - len2
        while j < len2:
            if chars1[offset + j] != chars2[j]:
                return False
            j += 1

        return True

    @elidable
    def ll_find_char(s, ch, start, end):
        i = start
        if end > len(s.chars):
            end = len(s.chars)
        while i < end:
            if s.chars[i] == ch:
                return i
            i += 1
        return -1
    ll_find_char._annenforceargs_ = [None, None, int, int]

    @elidable
    def ll_rfind_char(s, ch, start, end):
        if end > len(s.chars):
            end = len(s.chars)
        i = end
        while i > start:
            i -= 1
            if s.chars[i] == ch:
                return i
        return -1

    @elidable
    def ll_count_char(s, ch, start, end):
        count = 0
        i = start
        if end > len(s.chars):
            end = len(s.chars)
        while i < end:
            if s.chars[i] == ch:
                count += 1
            i += 1
        return count

    @classmethod
    def ll_find(cls, s1, s2, start, end):
        if start < 0:
            start = 0
        if end > len(s1.chars):
            end = len(s1.chars)
        if end - start < 0:
            return -1

        m = len(s2.chars)
        if m == 0:
            return start
        elif m == 1:
            return cls.ll_find_char(s1, s2.chars[0], start, end)

        return cls.ll_search(s1, s2, start, end, FAST_FIND)

    @classmethod
    def ll_rfind(cls, s1, s2, start, end):
        if start < 0:
            start = 0
        if end > len(s1.chars):
            end = len(s1.chars)
        if end - start < 0:
            return -1

        m = len(s2.chars)
        if m == 0:
            return end
        elif m == 1:
            return cls.ll_rfind_char(s1, s2.chars[0], start, end)

        return cls.ll_search(s1, s2, start, end, FAST_RFIND)

    @classmethod
    def ll_count(cls, s1, s2, start, end):
        if start < 0:
            start = 0
        if end > len(s1.chars):
            end = len(s1.chars)
        if end - start < 0:
            return 0

        m = len(s2.chars)
        if m == 0:
            return end - start + 1
        elif m == 1:
            return cls.ll_count_char(s1, s2.chars[0], start, end)

        res = cls.ll_search(s1, s2, start, end, FAST_COUNT)
        # For a few cases ll_search can return -1 to indicate an "impossible"
        # condition for a string match, count just returns 0 in these cases.
        if res < 0:
            res = 0
        return res

    @elidable
    def ll_search(s1, s2, start, end, mode):
        count = 0
        n = end - start
        m = len(s2.chars)

        w = n - m

        if w < 0:
            return -1

        mlast = m - 1
        skip = mlast - 1
        mask = 0

        if mode != FAST_RFIND:
            for i in range(mlast):
                mask = bloom_add(mask, s2.chars[i])
                if s2.chars[i] == s2.chars[mlast]:
                    skip = mlast - i - 1
            mask = bloom_add(mask, s2.chars[mlast])

            i = start - 1
            while i + 1 <= start + w:
                i += 1
                if s1.chars[i+m-1] == s2.chars[m-1]:
                    for j in range(mlast):
                        if s1.chars[i+j] != s2.chars[j]:
                            break
                    else:
                        if mode != FAST_COUNT:
                            return i
                        count += 1
                        i += mlast
                        continue

                    if i + m < len(s1.chars):
                        c = s1.chars[i + m]
                    else:
                        c = '\0'
                    if not bloom(mask, c):
                        i += m
                    else:
                        i += skip
                else:
                    if i + m < len(s1.chars):
                        c = s1.chars[i + m]
                    else:
                        c = '\0'
                    if not bloom(mask, c):
                        i += m
        else:
            mask = bloom_add(mask, s2.chars[0])
            for i in range(mlast, 0, -1):
                mask = bloom_add(mask, s2.chars[i])
                if s2.chars[i] == s2.chars[0]:
                    skip = i - 1

            i = start + w + 1
            while i - 1 >= start:
                i -= 1
                if s1.chars[i] == s2.chars[0]:
                    for j in xrange(mlast, 0, -1):
                        if s1.chars[i+j] != s2.chars[j]:
                            break
                    else:
                        return i
                    if i-1 >= 0 and not bloom(mask, s1.chars[i-1]):
                        i -= m
                    else:
                        i -= skip
                else:
                    if i-1 >= 0 and not bloom(mask, s1.chars[i-1]):
                        i -= m

        if mode != FAST_COUNT:
            return -1
        return count

    def ll_join_strs(length, items):
        num_items = length
        itemslen = 0
        i = 0
        while i < num_items:
            itemslen += len(items[i].chars)
            i += 1
        if typeOf(items).TO.OF.TO == STR:
            malloc = mallocstr
            copy_contents = copy_string_contents
        else:
            malloc = mallocunicode
            copy_contents = copy_unicode_contents
        result = malloc(itemslen)
        res_chars = result.chars
        res_index = 0
        i = 0
        while i < num_items:
            item_chars = items[i].chars
            item_len = len(item_chars)
            copy_contents(items[i], result, 0, res_index, item_len)
            res_index += item_len
            i += 1
        return result
    ll_join_strs._annenforceargs_ = [int, None]

    def ll_join_chars(length, chars, RES):
        # no need to optimize this, will be replaced by string builder
        # at some point soon
        num_chars = length
        if RES is StringRepr.lowleveltype:
            target = Char
            malloc = mallocstr
        else:
            target = UniChar
            malloc = mallocunicode
        result = malloc(num_chars)
        res_chars = result.chars
        i = 0
        while i < num_chars:
            res_chars[i] = cast_primitive(target, chars[i])
            i += 1
        return result

    @elidable
    def _ll_stringslice(s1, start, stop):
        lgt = stop - start
        assert start >= 0
        assert lgt >= 0
        newstr = s1.malloc(lgt)
        s1.copy_contents(s1, newstr, start, 0, lgt)
        return newstr
    _ll_stringslice.oopspec = 'stroruni.slice(s1, start, stop)'
    _ll_stringslice._annenforceargs_ = [None, int, int]

    def ll_stringslice_startonly(s1, start):
        return LLHelpers._ll_stringslice(s1, start, len(s1.chars))

    def ll_stringslice_startstop(s1, start, stop):
        if we_are_jitted():
            if stop > len(s1.chars):
                stop = len(s1.chars)
        else:
            if stop >= len(s1.chars):
                if start == 0:
                    return s1
                stop = len(s1.chars)
        return LLHelpers._ll_stringslice(s1, start, stop)

    def ll_stringslice_minusone(s1):
        newlen = len(s1.chars) - 1
        return LLHelpers._ll_stringslice(s1, 0, newlen)

    def ll_split_chr(LIST, s, c, max):
        chars = s.chars
        strlen = len(chars)
        count = 1
        i = 0
        if max == 0:
            i = strlen
        while i < strlen:
            if chars[i] == c:
                count += 1
                if max >= 0 and count > max:
                    break
            i += 1
        res = LIST.ll_newlist(count)
        items = res.ll_items()
        i = 0
        j = 0
        resindex = 0
        if max == 0:
            j = strlen
        while j < strlen:
            if chars[j] == c:
                item = items[resindex] = s.malloc(j - i)
                item.copy_contents(s, item, i, 0, j - i)
                resindex += 1
                i = j + 1
                if max >= 0 and resindex >= max:
                    j = strlen
                    break
            j += 1
        item = items[resindex] = s.malloc(j - i)
        item.copy_contents(s, item, i, 0, j - i)
        return res

    def ll_rsplit_chr(LIST, s, c, max):
        chars = s.chars
        strlen = len(chars)
        count = 1
        i = 0
        if max == 0:
            i = strlen
        while i < strlen:
            if chars[i] == c:
                count += 1
                if max >= 0 and count > max:
                    break
            i += 1
        res = LIST.ll_newlist(count)
        items = res.ll_items()
        i = strlen
        j = strlen
        resindex = count - 1
        assert resindex >= 0
        if max == 0:
            j = 0
        while j > 0:
            j -= 1
            if chars[j] == c:
                item = items[resindex] = s.malloc(i - j - 1)
                item.copy_contents(s, item, j + 1, 0, i - j - 1)
                resindex -= 1
                i = j
                if resindex == 0:
                    j = 0
                    break
        item = items[resindex] = s.malloc(i - j)
        item.copy_contents(s, item, j, 0, i - j)
        return res

    @elidable
    def ll_replace_chr_chr(s, c1, c2):
        length = len(s.chars)
        newstr = s.malloc(length)
        src = s.chars
        dst = newstr.chars
        j = 0
        while j < length:
            c = src[j]
            if c == c1:
                c = c2
            dst[j] = c
            j += 1
        return newstr

    @elidable
    def ll_contains(s, c):
        chars = s.chars
        strlen = len(chars)
        i = 0
        while i < strlen:
            if chars[i] == c:
                return True
            i += 1
        return False

    @elidable
    def ll_int(s, base):
        if not 2 <= base <= 36:
            raise ValueError
        chars = s.chars
        strlen = len(chars)
        i = 0
        #XXX: only space is allowed as white space for now
        while i < strlen and chars[i] == ' ':
            i += 1
        if not i < strlen:
            raise ValueError
        #check sign
        sign = 1
        if chars[i] == '-':
            sign = -1
            i += 1
        elif chars[i] == '+':
            i += 1;
        # skip whitespaces between sign and digits
        while i < strlen and chars[i] == ' ':
            i += 1
        #now get digits
        val = 0
        oldpos = i
        while i < strlen:
            c = ord(chars[i])
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
        while i < strlen and chars[i] == ' ':
            i += 1
        if not i == strlen:
            raise ValueError
        return sign * val

    # interface to build strings:
    #   x = ll_build_start(n)
    #   ll_build_push(x, next_string, 0)
    #   ll_build_push(x, next_string, 1)
    #   ...
    #   ll_build_push(x, next_string, n-1)
    #   s = ll_build_finish(x)

    def ll_build_start(parts_count):
        return malloc(TEMP, parts_count)

    def ll_build_push(builder, next_string, index):
        builder[index] = next_string

    def ll_build_finish(builder):
        return LLHelpers.ll_join_strs(len(builder), builder)

    def ll_constant(s):
        return string_repr.convert_const(s)
    ll_constant._annspecialcase_ = 'specialize:memo'

    def do_stringformat(cls, hop, sourcevarsrepr):
        s_str = hop.args_s[0]
        assert s_str.is_constant()
        s = s_str.const
        things = cls.parse_fmt_string(s)
        size = inputconst(Signed, len(things)) # could be unsigned?
        cTEMP = inputconst(Void, TEMP)
        cflags = inputconst(Void, {'flavor': 'gc'})
        vtemp = hop.genop("malloc_varsize", [cTEMP, cflags, size],
                          resulttype=Ptr(TEMP))

        argsiter = iter(sourcevarsrepr)

        InstanceRepr = hop.rtyper.type_system.rclass.InstanceRepr
        for i, thing in enumerate(things):
            if isinstance(thing, tuple):
                code = thing[0]
                vitem, r_arg = argsiter.next()
                if not hasattr(r_arg, 'll_str'):
                    raise TyperError("ll_str unsupported for: %r" % r_arg)
                if code == 's' or (code == 'r' and isinstance(r_arg, InstanceRepr)):
                    vchunk = hop.gendirectcall(r_arg.ll_str, vitem)
                elif code == 'd':
                    assert isinstance(r_arg, IntegerRepr)
                    #vchunk = hop.gendirectcall(r_arg.ll_str, vitem)
                    vchunk = hop.gendirectcall(ll_str.ll_int2dec, vitem)
                elif code == 'f':
                    #assert isinstance(r_arg, FloatRepr)
                    vchunk = hop.gendirectcall(r_arg.ll_str, vitem)
                elif code == 'x':
                    assert isinstance(r_arg, IntegerRepr)
                    vchunk = hop.gendirectcall(ll_str.ll_int2hex, vitem,
                                               inputconst(Bool, False))
                elif code == 'o':
                    assert isinstance(r_arg, IntegerRepr)
                    vchunk = hop.gendirectcall(ll_str.ll_int2oct, vitem,
                                               inputconst(Bool, False))
                else:
                    raise TyperError, "%%%s is not RPython" % (code, )
            else:
                from pypy.rpython.lltypesystem.rstr import string_repr
                vchunk = inputconst(string_repr, thing)
            i = inputconst(Signed, i)
            hop.genop('setarrayitem', [vtemp, i, vchunk])

        hop.exception_cannot_occur()   # to ignore the ZeroDivisionError of '%'
        return hop.gendirectcall(cls.ll_join_strs, size, vtemp)
    do_stringformat = classmethod(do_stringformat)

TEMP = GcArray(Ptr(STR))

# ____________________________________________________________

STR.become(GcStruct('rpy_string', ('hash',  Signed),
                    ('chars', Array(Char, hints={'immutable': True})),
                    adtmeths={'malloc' : staticAdtMethod(mallocstr),
                              'empty'  : staticAdtMethod(emptystrfun),
                              'copy_contents' : staticAdtMethod(copy_string_contents),
                              'gethash': LLHelpers.ll_strhash}))
UNICODE.become(GcStruct('rpy_unicode', ('hash', Signed),
                        ('chars', Array(UniChar, hints={'immutable': True})),
                        adtmeths={'malloc' : staticAdtMethod(mallocunicode),
                                  'empty'  : staticAdtMethod(emptyunicodefun),
                                  'copy_contents' : staticAdtMethod(copy_unicode_contents),
                                  'gethash': LLHelpers.ll_strhash}
                        ))


# TODO: make the public interface of the rstr module cleaner
ll_strconcat = LLHelpers.ll_strconcat
ll_join = LLHelpers.ll_join
ll_str2unicode = LLHelpers.ll_str2unicode
do_stringformat = LLHelpers.do_stringformat

string_repr = StringRepr()
char_repr = CharRepr()
unichar_repr = UniCharRepr()
char_repr.ll = LLHelpers
unichar_repr.ll = LLHelpers
unicode_repr = UnicodeRepr()
emptystr = string_repr.convert_const("")
emptyunicode = unicode_repr.convert_const(u'')

StringRepr.repr = string_repr
UnicodeRepr.repr = unicode_repr
UniCharRepr.repr = unicode_repr
UniCharRepr.char_repr = unichar_repr
UnicodeRepr.char_repr = unichar_repr
CharRepr.char_repr = char_repr
StringRepr.char_repr = char_repr

class BaseStringIteratorRepr(AbstractStringIteratorRepr):

    def __init__(self):
        self.ll_striter = ll_striter
        self.ll_strnext = ll_strnext

class StringIteratorRepr(BaseStringIteratorRepr):

    lowleveltype = Ptr(GcStruct('stringiter',
                                ('string', string_repr.lowleveltype),
                                ('index', Signed)))

class UnicodeIteratorRepr(BaseStringIteratorRepr):

    lowleveltype = Ptr(GcStruct('unicodeiter',
                                ('string', unicode_repr.lowleveltype),
                                ('index', Signed)))

def ll_striter(string):
    if typeOf(string) == string_repr.lowleveltype:
        TP = string_repr.iterator_repr.lowleveltype.TO
    elif typeOf(string) == unicode_repr.lowleveltype:
        TP = unicode_repr.iterator_repr.lowleveltype.TO
    else:
        raise TypeError("Unknown string type %s" % (typeOf(string),))
    iter = malloc(TP)
    iter.string = string
    iter.index = 0
    return iter

def ll_strnext(iter):
    chars = iter.string.chars
    index = iter.index
    if index >= len(chars):
        raise StopIteration
    iter.index = index + 1
    return chars[index]

string_repr.iterator_repr = StringIteratorRepr()
unicode_repr.iterator_repr = UnicodeIteratorRepr()

# these should be in rclass, but circular imports prevent (also it's
# not that insane that a string constant is built in this file).

instance_str_prefix = string_repr.convert_const("<")
instance_str_infix  = string_repr.convert_const(" object at 0x")
instance_str_suffix = string_repr.convert_const(">")

null_str = string_repr.convert_const("NULL")

unboxed_instance_str_prefix = string_repr.convert_const("<unboxed ")
unboxed_instance_str_suffix = string_repr.convert_const(">")
