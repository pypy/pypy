from weakref import WeakValueDictionary

from rpython.annotator import model as annmodel
from rpython.rlib import jit, types
from rpython.rlib.debug import ll_assert
from rpython.rlib.objectmodel import (malloc_zero_filled, we_are_translated,
    _hash_string, keepalive_until_here, specialize)
from rpython.rlib.signature import signature
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.error import TyperError
from rpython.rtyper.lltypesystem import ll_str, llmemory
from rpython.rtyper.lltypesystem.lltype import (GcStruct, Signed, Array, Char,
    UniChar, Ptr, malloc, Bool, Void, GcArray, nullptr, cast_primitive,
    typeOf, staticAdtMethod, GcForwardReference)
from rpython.rtyper.rmodel import inputconst, Repr, IntegerRepr
from rpython.rtyper.rstr import (AbstractStringRepr, AbstractCharRepr,
    AbstractUniCharRepr, AbstractStringIteratorRepr, AbstractLLHelpers,
    AbstractUnicodeRepr)
from rpython.tool.sourcetools import func_with_new_name

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

def _new_copy_contents_fun(SRC_TP, DST_TP, CHAR_TP, name):
    @specialize.arg(0)
    def _str_ofs(TP, item):
        return (llmemory.offsetof(TP, 'chars') +
                llmemory.itemoffsetof(TP.chars, 0) +
                llmemory.sizeof(CHAR_TP) * item)

    @signature(types.any(), types.any(), types.int(), returns=types.any())
    @specialize.arg(0)
    def _get_raw_buf(TP, src, ofs):
        assert typeOf(src).TO == TP
        assert ofs >= 0
        return llmemory.cast_ptr_to_adr(src) + _str_ofs(TP, ofs)
    _get_raw_buf._always_inline_ = True

    @jit.oopspec('stroruni.copy_contents(src, dst, srcstart, dststart, length)')
    @signature(types.any(), types.any(), types.int(), types.int(), types.int(), returns=types.none())
    def copy_string_contents(src, dst, srcstart, dststart, length):
        """Copies 'length' characters from the 'src' string to the 'dst'
        string, starting at position 'srcstart' and 'dststart'."""
        # xxx Warning: don't try to do this at home.  It relies on a lot
        # of details to be sure that it works correctly in all cases.
        # Notably: no GC operation at all from the first cast_ptr_to_adr()
        # because it might move the strings.  The keepalive_until_here()
        # are obscurely essential to make sure that the strings stay alive
        # longer than the raw_memcopy().
        assert length >= 0
        # from here, no GC operations can happen
        src = _get_raw_buf(SRC_TP, src, srcstart)
        dst = _get_raw_buf(DST_TP, dst, dststart)
        llmemory.raw_memcopy(src, dst, llmemory.sizeof(CHAR_TP) * length)
        # end of "no GC" section
        keepalive_until_here(src)
        keepalive_until_here(dst)
    copy_string_contents._always_inline_ = True
    copy_string_contents = func_with_new_name(copy_string_contents,
                                              'copy_%s_contents' % name)

    @jit.oopspec('stroruni.copy_string_to_raw(src, ptrdst, srcstart, length)')
    def copy_string_to_raw(src, ptrdst, srcstart, length):
        """
        Copies 'length' characters from the 'src' string to the 'ptrdst'
        buffer, starting at position 'srcstart'.
        'ptrdst' must be a non-gc Array of Char.
        """
        # xxx Warning: same note as above apply: don't do this at home
        assert length >= 0
        # from here, no GC operations can happen
        src = _get_raw_buf(SRC_TP, src, srcstart)
        adr = llmemory.cast_ptr_to_adr(ptrdst)
        dstbuf = adr + llmemory.itemoffsetof(typeOf(ptrdst).TO, 0)
        llmemory.raw_memcopy(src, dstbuf, llmemory.sizeof(CHAR_TP) * length)
        # end of "no GC" section
        keepalive_until_here(src)
    copy_string_to_raw._always_inline_ = True
    copy_string_to_raw = func_with_new_name(copy_string_to_raw, 'copy_%s_to_raw' % name)

    return copy_string_to_raw, copy_string_contents

copy_string_to_raw, copy_string_contents = _new_copy_contents_fun(STR, STR, Char, 'string')
copy_unicode_to_raw, copy_unicode_contents = _new_copy_contents_fun(UNICODE, UNICODE,
                                                                    UniChar, 'unicode')

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
        return self.repr.iterator_repr

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

    @jit.elidable
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

    @jit.elidable
    def ll_unicode(self, s):
        if s:
            return s
        else:
            return self.ll.ll_constant_unicode(u'None')

    @jit.elidable
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



# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.
#

FAST_COUNT = 0
FAST_FIND = 1
FAST_RFIND = 2


from rpython.rlib.rarithmetic import LONG_BIT as BLOOM_WIDTH


def bloom_add(mask, c):
    return mask | (1 << (ord(c) & (BLOOM_WIDTH - 1)))


def bloom(mask, c):
    return mask & (1 << (ord(c) & (BLOOM_WIDTH - 1)))


class LLHelpers(AbstractLLHelpers):
    from rpython.rtyper.annlowlevel import llstr, llunicode

    @jit.elidable
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

    @jit.elidable
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

    @signature(types.any(), types.int(), returns=types.any())
    def ll_stritem_nonneg(s, i):
        chars = s.chars
        ll_assert(i >= 0, "negative str getitem index")
        ll_assert(i < len(chars), "str getitem index out of bound")
        return chars[i]

    def ll_chr2str(ch):
        if typeOf(ch) is Char:
            malloc = mallocstr
        else:
            malloc = mallocunicode
        s = malloc(1)
        s.chars[0] = ch
        return s

    # @jit.look_inside_iff(lambda str: jit.isconstant(len(str.chars)) and len(str.chars) == 1)
    @jit.oopspec("str.str2unicode(str)")
    def ll_str2unicode(str):
        lgt = len(str.chars)
        s = mallocunicode(lgt)
        for i in range(lgt):
            if ord(str.chars[i]) > 127:
                raise UnicodeDecodeError
            s.chars[i] = cast_primitive(UniChar, str.chars[i])
        return s

    def ll_str2bytearray(str):
        from rpython.rtyper.lltypesystem.rbytearray import BYTEARRAY

        lgt = len(str.chars)
        b = malloc(BYTEARRAY, lgt)
        for i in range(lgt):
            b.chars[i] = str.chars[i]
        return b

    @jit.elidable
    def ll_strhash(s):
        # unlike CPython, there is no reason to avoid to return -1
        # but our malloc initializes the memory to zero, so we use zero as the
        # special non-computed-yet value.
        if not s:
            return 0
        x = s.hash
        if x == 0:
            x = _hash_string(s.chars)
            if x == 0:
                x = 29872897
            s.hash = x
        return x

    def ll_length(s):
        return len(s.chars)

    def ll_strfasthash(s):
        return s.hash     # assumes that the hash is already computed

    @jit.elidable
    def ll_strconcat(s1, s2):
        len1 = s1.length()
        len2 = s2.length()
        # a single '+' like this is allowed to overflow: it gets
        # a negative result, and the gc will complain
        # the typechecks below are if TP == BYTEARRAY
        if typeOf(s1) == Ptr(STR):
            newstr = s2.malloc(len1 + len2)
            newstr.copy_contents_from_str(s1, newstr, 0, 0, len1)
        else:
            newstr = s1.malloc(len1 + len2)
            newstr.copy_contents(s1, newstr, 0, 0, len1)
        if typeOf(s2) == Ptr(STR):
            newstr.copy_contents_from_str(s2, newstr, 0, len1, len2)
        else:
            newstr.copy_contents(s2, newstr, 0, len1, len2)
        return newstr
    ll_strconcat.oopspec = 'stroruni.concat(s1, s2)'

    @jit.elidable
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
            while lpos < rpos + 1 and s.chars[rpos] == ch:
                rpos -= 1
        if rpos < lpos:
            return s.empty()
        r_len = rpos - lpos + 1
        result = s.malloc(r_len)
        s.copy_contents(s, result, lpos, 0, r_len)
        return result

    @jit.elidable
    def ll_upper(s):
        s_chars = s.chars
        s_len = len(s_chars)
        if s_len == 0:
            return s.empty()
        i = 0
        result = mallocstr(s_len)
        #        ^^^^^^^^^ specifically to explode on unicode
        while i < s_len:
            result.chars[i] = LLHelpers.ll_upper_char(s_chars[i])
            i += 1
        return result

    @jit.elidable
    def ll_lower(s):
        s_chars = s.chars
        s_len = len(s_chars)
        if s_len == 0:
            return s.empty()
        i = 0
        result = mallocstr(s_len)
        #        ^^^^^^^^^ specifically to explode on unicode
        while i < s_len:
            result.chars[i] = LLHelpers.ll_lower_char(s_chars[i])
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
            try:
                itemslen = ovfcheck(itemslen + len(items[i].chars))
            except OverflowError:
                raise MemoryError
            i += 1
        try:
            seplen = ovfcheck(s_len * (num_items - 1))
        except OverflowError:
            raise MemoryError
        # a single '+' at the end is allowed to overflow: it gets
        # a negative result, and the gc will complain
        result = s.malloc(itemslen + seplen)
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

    @jit.elidable
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

    @jit.elidable
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

    @jit.elidable
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

    def ll_startswith_char(s, ch):
        if not len(s.chars):
            return False
        return s.chars[0] == ch

    @jit.elidable
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

    def ll_endswith_char(s, ch):
        if not len(s.chars):
            return False
        return s.chars[len(s.chars) - 1] == ch

    @jit.elidable
    @signature(types.any(), types.any(), types.int(), types.int(), returns=types.int())
    def ll_find_char(s, ch, start, end):
        i = start
        if end > len(s.chars):
            end = len(s.chars)
        while i < end:
            if s.chars[i] == ch:
                return i
            i += 1
        return -1

    @jit.elidable
    def ll_rfind_char(s, ch, start, end):
        if end > len(s.chars):
            end = len(s.chars)
        i = end
        while i > start:
            i -= 1
            if s.chars[i] == ch:
                return i
        return -1

    @jit.elidable
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
        if m == 1:
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
        if m == 1:
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
        if m == 1:
            return cls.ll_count_char(s1, s2.chars[0], start, end)

        res = cls.ll_search(s1, s2, start, end, FAST_COUNT)
        # For a few cases ll_search can return -1 to indicate an "impossible"
        # condition for a string match, count just returns 0 in these cases.
        if res < 0:
            res = 0
        return res

    @jit.elidable
    def ll_search(s1, s2, start, end, mode):
        count = 0
        n = end - start
        m = len(s2.chars)

        if m == 0:
            if mode == FAST_COUNT:
                return end - start + 1
            elif mode == FAST_RFIND:
                return end
            else:
                return start

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
                if s1.chars[i + m - 1] == s2.chars[m - 1]:
                    for j in range(mlast):
                        if s1.chars[i + j] != s2.chars[j]:
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
                        if s1.chars[i + j] != s2.chars[j]:
                            break
                    else:
                        return i
                    if i - 1 >= 0 and not bloom(mask, s1.chars[i - 1]):
                        i -= m
                    else:
                        i -= skip
                else:
                    if i - 1 >= 0 and not bloom(mask, s1.chars[i - 1]):
                        i -= m

        if mode != FAST_COUNT:
            return -1
        return count

    @signature(types.int(), types.any(), returns=types.any())
    @jit.look_inside_iff(lambda length, items: jit.loop_unrolling_heuristic(
        items, length))
    def ll_join_strs(length, items):
        # Special case for length 1 items, helps both the JIT and other code
        if length == 1:
            return items[0]

        num_items = length
        itemslen = 0
        i = 0
        while i < num_items:
            try:
                itemslen = ovfcheck(itemslen + len(items[i].chars))
            except OverflowError:
                raise MemoryError
            i += 1
        if typeOf(items).TO.OF.TO == STR:
            malloc = mallocstr
            copy_contents = copy_string_contents
        else:
            malloc = mallocunicode
            copy_contents = copy_unicode_contents
        result = malloc(itemslen)
        res_index = 0
        i = 0
        while i < num_items:
            item_chars = items[i].chars
            item_len = len(item_chars)
            copy_contents(items[i], result, 0, res_index, item_len)
            res_index += item_len
            i += 1
        return result

    @jit.look_inside_iff(lambda length, chars, RES: jit.isconstant(length) and jit.isvirtual(chars))
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

    @jit.oopspec('stroruni.slice(s1, start, stop)')
    @signature(types.any(), types.int(), types.int(), returns=types.any())
    @jit.elidable
    def _ll_stringslice(s1, start, stop):
        lgt = stop - start
        assert start >= 0
        # If start > stop, return a empty string. This can happen if the start
        # is greater than the length of the string. Use < instead of <= to avoid
        # creating another path for the JIT when start == stop.
        if lgt < 0:
            return s1.empty()
        newstr = s1.malloc(lgt)
        s1.copy_contents(s1, newstr, start, 0, lgt)
        return newstr

    def ll_stringslice_startonly(s1, start):
        return LLHelpers._ll_stringslice(s1, start, len(s1.chars))

    def ll_stringslice_startstop(s1, start, stop):
        if jit.we_are_jitted():
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

    @jit.elidable
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

    @jit.elidable
    def ll_contains(s, c):
        chars = s.chars
        strlen = len(chars)
        i = 0
        while i < strlen:
            if chars[i] == c:
                return True
            i += 1
        return False

    @jit.elidable
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
            i += 1
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

    @specialize.memo()
    def ll_constant(s):
        return string_repr.convert_const(s)

    @specialize.memo()
    def ll_constant_unicode(s):
        return unicode_repr.convert_const(s)

    def do_stringformat(cls, hop, sourcevarsrepr):
        s_str = hop.args_s[0]
        assert s_str.is_constant()
        is_unicode = isinstance(s_str, annmodel.SomeUnicodeString)
        if is_unicode:
            TEMPBUF = TEMP_UNICODE
        else:
            TEMPBUF = TEMP
        s = s_str.const
        things = cls.parse_fmt_string(s)
        size = inputconst(Signed, len(things)) # could be unsigned?
        cTEMP = inputconst(Void, TEMPBUF)
        cflags = inputconst(Void, {'flavor': 'gc'})
        vtemp = hop.genop("malloc_varsize", [cTEMP, cflags, size],
                          resulttype=Ptr(TEMPBUF))

        argsiter = iter(sourcevarsrepr)

        from rpython.rtyper.lltypesystem.rclass import InstanceRepr
        for i, thing in enumerate(things):
            if isinstance(thing, tuple):
                code = thing[0]
                vitem, r_arg = argsiter.next()
                if not hasattr(r_arg, 'll_str'):
                    raise TyperError("ll_str unsupported for: %r" % r_arg)
                if code == 's':
                    if is_unicode:
                        # only UniCharRepr and UnicodeRepr has it so far
                        vchunk = hop.gendirectcall(r_arg.ll_unicode, vitem)
                    else:
                        vchunk = hop.gendirectcall(r_arg.ll_str, vitem)
                elif code == 'r' and isinstance(r_arg, InstanceRepr):
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
                    raise TyperError("%%%s is not RPython" % (code,))
            else:
                if is_unicode:
                    vchunk = inputconst(unicode_repr, thing)
                else:
                    vchunk = inputconst(string_repr, thing)
            i = inputconst(Signed, i)
            if is_unicode and vchunk.concretetype != Ptr(UNICODE):
                # if we are here, one of the ll_str.* functions returned some
                # STR, so we convert it to unicode. It's a bit suboptimal
                # because we do one extra copy.
                vchunk = hop.gendirectcall(cls.ll_str2unicode, vchunk)
            hop.genop('setarrayitem', [vtemp, i, vchunk])

        hop.exception_cannot_occur()   # to ignore the ZeroDivisionError of '%'
        return hop.gendirectcall(cls.ll_join_strs, size, vtemp)
    do_stringformat = classmethod(do_stringformat)

TEMP = GcArray(Ptr(STR))
TEMP_UNICODE = GcArray(Ptr(UNICODE))

# ____________________________________________________________

STR.become(GcStruct('rpy_string', ('hash',  Signed),
                    ('chars', Array(Char, hints={'immutable': True})),
                    adtmeths={'malloc' : staticAdtMethod(mallocstr),
                              'empty'  : staticAdtMethod(emptystrfun),
                              'copy_contents' : staticAdtMethod(copy_string_contents),
                              'copy_contents_from_str' : staticAdtMethod(copy_string_contents),
                              'gethash': LLHelpers.ll_strhash,
                              'length': LLHelpers.ll_length}))
UNICODE.become(GcStruct('rpy_unicode', ('hash', Signed),
                        ('chars', Array(UniChar, hints={'immutable': True})),
                        adtmeths={'malloc' : staticAdtMethod(mallocunicode),
                                  'empty'  : staticAdtMethod(emptyunicodefun),
                                  'copy_contents' : staticAdtMethod(copy_unicode_contents),
                                  'copy_contents_from_str' : staticAdtMethod(copy_unicode_contents),
                                  'gethash': LLHelpers.ll_strhash,
                                  'length': LLHelpers.ll_length}
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
        self.ll_getnextindex = ll_getnextindex

class StringIteratorRepr(BaseStringIteratorRepr):

    external_item_repr = char_repr
    lowleveltype = Ptr(GcStruct('stringiter',
                                ('string', string_repr.lowleveltype),
                                ('index', Signed)))

class UnicodeIteratorRepr(BaseStringIteratorRepr):

    external_item_repr = unichar_repr
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

def ll_getnextindex(iter):
    return iter.index

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
