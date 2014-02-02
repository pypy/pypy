"""Functionality shared between bytes/bytearray/unicode"""

from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rlib.rstring import endswith, replace, rsplit, split, startswith

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import WrappedDefault, unwrap_spec
from pypy.objspace.std import slicetype
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice


class StringMethods(object):
    def _sliced(self, space, s, start, stop, orig_obj):
        assert start >= 0
        assert stop >= 0
        #if start == 0 and stop == len(s) and space.is_w(space.type(orig_obj),
        #                                                space.w_str):
        #    return orig_obj
        return self._new(s[start:stop])

    @specialize.arg(4)
    def _convert_idx_params(self, space, w_start, w_end, upper_bound=False):
        value = self._val(space)
        lenself = len(value)
        start, end = slicetype.unwrap_start_stop(
            space, lenself, w_start, w_end, upper_bound=upper_bound)
        return (value, start, end)

    def descr_len(self, space):
        return space.wrap(self._len())

    #def descr_iter(self, space):
    #    pass

    def descr_contains(self, space, w_sub):
        value = self._val(space)
        other = self._op_val(space, w_sub)
        return space.newbool(value.find(other) >= 0)

    def descr_add(self, space, w_other):
        try:
            other = self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return self._new(self._val(space) + other)

    def descr_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        if times <= 0:
            return self._empty()
        if self._len() == 1:
            return self._new(self._val(space)[0] * times)
        return self._new(self._val(space) * times)

    descr_rmul = descr_mul

    def descr_getitem(self, space, w_index):
        if isinstance(w_index, W_SliceObject):
            selfvalue = self._val(space)
            length = len(selfvalue)
            start, stop, step, sl = w_index.indices4(space, length)
            if sl == 0:
                return self._empty()
            elif step == 1:
                assert start >= 0 and stop >= 0
                return self._sliced(space, selfvalue, start, stop, self)
            else:
                ret = _descr_getslice_slowpath(selfvalue, start, step, sl)
                return self._new_from_list(ret)

        index = space.getindex_w(w_index, space.w_IndexError, "string index")
        selfvalue = self._val(space)
        selflen = len(selfvalue)
        if index < 0:
            index += selflen
        if index < 0 or index >= selflen:
            raise operationerrfmt(space.w_IndexError,
                                  "string index out of range")
        from pypy.objspace.std.bytearrayobject import W_BytearrayObject
        if isinstance(self, W_BytearrayObject):
            return space.wrap(ord(selfvalue[index]))
        return self._new(selfvalue[index])

    def descr_getslice(self, space, w_start, w_stop):
        selfvalue = self._val(space)
        start, stop = normalize_simple_slice(space, len(selfvalue), w_start,
                                             w_stop)
        if start == stop:
            return self._empty()
        else:
            return self._sliced(space, selfvalue, start, stop, self)

    def descr_capitalize(self, space):
        value = self._val(space)
        if len(value) == 0:
            return self._empty()

        builder = self._builder(len(value))
        builder.append(self._upper(value[0]))
        for i in range(1, len(value)):
            builder.append(self._lower(value[i]))
        return self._new(builder.build())

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_center(self, space, width, w_fillchar):
        value = self._val(space)
        fillchar = self._op_val(space, w_fillchar)
        if len(fillchar) != 1:
            raise operationerrfmt(space.w_TypeError,
                                  "center() argument 2 must be a single "
                                  "character")

        d = width - len(value)
        if d > 0:
            offset = d//2 + (d & width & 1)
            fillchar = fillchar[0]    # annotator hint: it's a single character
            centered = offset * fillchar + value + (d - offset) * fillchar
        else:
            centered = value

        return self._new(centered)

    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        value, start, end = self._convert_idx_params(space, w_start, w_end)
        return space.newint(value.count(self._op_val(space, w_sub), start,
                                        end))

    def descr_decode(self, space, w_encoding=None, w_errors=None):
        from pypy.objspace.std.unicodeobject import (
            _get_encoding_and_errors, decode_object, unicode_from_string)
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        if encoding is None and errors is None:
            return unicode_from_string(space, self)
        return decode_object(space, self, encoding, errors)

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        from pypy.objspace.std.unicodeobject import (
            _get_encoding_and_errors, encode_object)
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        return encode_object(space, self, encoding, errors)

    @unwrap_spec(tabsize=int)
    def descr_expandtabs(self, space, tabsize=8):
        value = self._val(space)
        if not value:
            return self._empty()

        splitted = value.split(self._chr('\t'))
        try:
            ovfcheck(len(splitted) * tabsize)
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "new string is too long")
        expanded = oldtoken = splitted.pop(0)

        for token in splitted:
            expanded += self._chr(' ') * self._tabindent(oldtoken,
                                                         tabsize) + token
            oldtoken = token

        return self._new(expanded)

    def _tabindent(self, token, tabsize):
        """calculates distance behind the token to the next tabstop"""

        distance = tabsize
        if token:
            distance = 0
            offset = len(token)

            while 1:
                if token[offset-1] == "\n" or token[offset-1] == "\r":
                    break
                distance += 1
                offset -= 1
                if offset == 0:
                    break

            # the same like distance = len(token) - (offset + 1)
            distance = (tabsize - distance) % tabsize
            if distance == 0:
                distance = tabsize

        return distance

    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        (value, start, end) = self._convert_idx_params(space, w_start, w_end)
        res = value.find(self._op_val(space, w_sub), start, end)
        return space.wrap(res)

    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        (value, start, end) = self._convert_idx_params(space, w_start, w_end)
        res = value.rfind(self._op_val(space, w_sub), start, end)
        return space.wrap(res)

    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        (value, start, end) = self._convert_idx_params(space, w_start, w_end)
        res = value.find(self._op_val(space, w_sub), start, end)
        if res < 0:
            raise operationerrfmt(space.w_ValueError,
                                  "substring not found in string.index")

        return space.wrap(res)

    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        (value, start, end) = self._convert_idx_params(space, w_start, w_end)
        res = value.rfind(self._op_val(space, w_sub), start, end)
        if res < 0:
            raise operationerrfmt(space.w_ValueError,
                                  "substring not found in string.rindex")

        return space.wrap(res)

    @specialize.arg(2)
    def _is_generic(self, space, func_name):
        func = getattr(self, func_name)
        v = self._val(space)
        if len(v) == 0:
            return space.w_False
        if len(v) == 1:
            c = v[0]
            return space.newbool(func(c))
        else:
            return self._is_generic_loop(space, v, func_name)

    @specialize.arg(3)
    def _is_generic_loop(self, space, v, func_name):
        func = getattr(self, func_name)
        for idx in range(len(v)):
            if not func(v[idx]):
                return space.w_False
        return space.w_True

    def descr_isalnum(self, space):
        return self._is_generic(space, '_isalnum')

    def descr_isalpha(self, space):
        return self._is_generic(space, '_isalpha')

    def descr_isdigit(self, space):
        return self._is_generic(space, '_isdigit')

    # this is only for bytes and bytesarray: unicodeobject overrides it
    def _descr_islower_slowpath(self, space, v):
        cased = False
        for idx in range(len(v)):
            if self._isupper(v[idx]):
                return False
            elif not cased and self._islower(v[idx]):
                cased = True
        return cased

    def descr_islower(self, space):
        v = self._val(space)
        if len(v) == 1:
            c = v[0]
            return space.newbool(self._islower(c))
        cased = self._descr_islower_slowpath(space, v)
        return space.newbool(cased)

    def descr_isspace(self, space):
        return self._is_generic(space, '_isspace')

    def descr_istitle(self, space):
        input = self._val(space)
        cased = False
        previous_is_cased = False

        for pos in range(0, len(input)):
            ch = input[pos]
            if self._istitle(ch):
                if previous_is_cased:
                    return space.w_False
                previous_is_cased = True
                cased = True
            elif self._islower(ch):
                if not previous_is_cased:
                    return space.w_False
                cased = True
            else:
                previous_is_cased = False

        return space.newbool(cased)

    # this is only for bytes and bytesarray: unicodeobject overrides it
    def _descr_isupper_slowpath(self, space, v):
        cased = False
        for idx in range(len(v)):
            if self._islower(v[idx]):
                return False
            elif not cased and self._isupper(v[idx]):
                cased = True
        return cased

    def descr_isupper(self, space):
        v = self._val(space)
        if len(v) == 1:
            c = v[0]
            return space.newbool(self._isupper(c))
        cased = self._descr_isupper_slowpath(space, v)
        return space.newbool(cased)

    def descr_join(self, space, w_list):
        list_w = space.listview(w_list)
        size = len(list_w)

        if size == 0:
            return self._empty()

        if size == 1:
            w_s = list_w[0]
            # only one item, return it if it's not a subclass of str
            if self._join_return_one(space, w_s):
                return w_s

        return self._str_join_many_items(space, list_w, size)

    @jit.look_inside_iff(lambda self, space, list_w, size:
                         jit.loop_unrolling_heuristic(list_w, size))
    def _str_join_many_items(self, space, list_w, size):
        value = self._val(space)

        prealloc_size = len(value) * (size - 1)
        for i in range(size):
            w_s = list_w[i]
            check_item = self._join_check_item(space, w_s)
            if check_item == 1:
                raise operationerrfmt(
                    space.w_TypeError,
                    "sequence item %d: expected string, %T found", i, w_s)
            elif check_item == 2:
                return self._join_autoconvert(space, list_w)
            prealloc_size += len(self._op_val(space, w_s))

        sb = self._builder(prealloc_size)
        for i in range(size):
            if value and i != 0:
                sb.append(value)
            sb.append(self._op_val(space, list_w[i]))
        return self._new(sb.build())

    def _join_autoconvert(self, space, list_w):
        assert False, 'unreachable'

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_ljust(self, space, width, w_fillchar):
        value = self._val(space)
        fillchar = self._op_val(space, w_fillchar)
        if len(fillchar) != 1:
            raise operationerrfmt(space.w_TypeError,
                                  "ljust() argument 2 must be a single "
                                  "character")
        d = width - len(value)
        if d > 0:
            fillchar = fillchar[0]    # annotator hint: it's a single character
            value += d * fillchar

        return self._new(value)

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_rjust(self, space, width, w_fillchar):
        value = self._val(space)
        fillchar = self._op_val(space, w_fillchar)
        if len(fillchar) != 1:
            raise operationerrfmt(space.w_TypeError,
                                  "rjust() argument 2 must be a single "
                                  "character")
        d = width - len(value)
        if d > 0:
            fillchar = fillchar[0]    # annotator hint: it's a single character
            value = d * fillchar + value

        return self._new(value)

    def descr_lower(self, space):
        value = self._val(space)
        builder = self._builder(len(value))
        for i in range(len(value)):
            builder.append(self._lower(value[i]))
        return self._new(builder.build())

    def descr_partition(self, space, w_sub):
        value = self._val(space)
        sub = self._op_val(space, w_sub)
        if not sub:
            raise operationerrfmt(space.w_ValueError, "empty separator")
        pos = value.find(sub)
        if pos == -1:
            from pypy.objspace.std.bytearrayobject import W_BytearrayObject
            if isinstance(self, W_BytearrayObject):
                self = self._new(value)
            return space.newtuple([self, self._empty(), self._empty()])
        else:
            from pypy.objspace.std.bytearrayobject import W_BytearrayObject
            if isinstance(self, W_BytearrayObject):
                w_sub = self._new(sub)
            return space.newtuple(
                [self._sliced(space, value, 0, pos, self), w_sub,
                 self._sliced(space, value, pos+len(sub), len(value), self)])

    def descr_rpartition(self, space, w_sub):
        value = self._val(space)
        sub = self._op_val(space, w_sub)
        if not sub:
            raise operationerrfmt(space.w_ValueError, "empty separator")
        pos = value.rfind(sub)
        if pos == -1:
            from pypy.objspace.std.bytearrayobject import W_BytearrayObject
            if isinstance(self, W_BytearrayObject):
                self = self._new(value)
            return space.newtuple([self._empty(), self._empty(), self])
        else:
            from pypy.objspace.std.bytearrayobject import W_BytearrayObject
            if isinstance(self, W_BytearrayObject):
                w_sub = self._new(sub)
            return space.newtuple(
                [self._sliced(space, value, 0, pos, self), w_sub,
                 self._sliced(space, value, pos+len(sub), len(value), self)])

    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        input = self._val(space)
        sub = self._op_val(space, w_old)
        by = self._op_val(space, w_new)
        try:
            res = replace(input, sub, by, count)
        except OverflowError:
            raise operationerrfmt(space.w_OverflowError,
                                  "replace string is too long")
        return self._new(res)

    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        res = []
        value = self._val(space)
        length = len(value)
        if space.is_none(w_sep):
            res = split(value, maxsplit=maxsplit)
            return self._newlist_unwrapped(space, res)

        by = self._op_val(space, w_sep)
        bylen = len(by)
        if bylen == 0:
            raise operationerrfmt(space.w_ValueError, "empty separator")
        res = split(value, by, maxsplit)
        return self._newlist_unwrapped(space, res)

    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        res = []
        value = self._val(space)
        if space.is_none(w_sep):
            res = rsplit(value, maxsplit=maxsplit)
            return self._newlist_unwrapped(space, res)

        by = self._op_val(space, w_sep)
        bylen = len(by)
        if bylen == 0:
            raise operationerrfmt(space.w_ValueError, "empty separator")
        res = rsplit(value, by, maxsplit)
        return self._newlist_unwrapped(space, res)

    @unwrap_spec(keepends=bool)
    def descr_splitlines(self, space, keepends=False):
        value = self._val(space)
        length = len(value)
        strs = []
        pos = 0
        while pos < length:
            sol = pos
            while pos < length and not self._islinebreak(value[pos]):
                pos += 1
            eol = pos
            pos += 1
            # read CRLF as one line break
            if pos < length and value[eol] == '\r' and value[pos] == '\n':
                pos += 1
            if keepends:
                eol = pos
            strs.append(value[sol:eol])
        if pos < length:
            strs.append(value[pos:length])
        return self._newlist_unwrapped(space, strs)

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        (value, start, end) = self._convert_idx_params(space, w_start, w_end,
                                                       True)
        if space.isinstance_w(w_prefix, space.w_tuple):
            for w_prefix in space.fixedview(w_prefix):
                if self._startswith(space, value, w_prefix, start, end):
                    return space.w_True
            return space.w_False
        return space.newbool(self._startswith(space, value, w_prefix, start,
                                              end))

    def _startswith(self, space, value, w_prefix, start, end):
        return startswith(value, self._op_val(space, w_prefix), start, end)

    def descr_endswith(self, space, w_suffix, w_start=None, w_end=None):
        (value, start, end) = self._convert_idx_params(space, w_start, w_end,
                                                       True)
        if space.isinstance_w(w_suffix, space.w_tuple):
            for w_suffix in space.fixedview(w_suffix):
                if self._endswith(space, value, w_suffix, start, end):
                    return space.w_True
            return space.w_False
        return space.newbool(self._endswith(space, value, w_suffix, start,
                                            end))

    def _endswith(self, space, value, w_prefix, start, end):
        return endswith(value, self._op_val(space, w_prefix), start, end)

    def _strip(self, space, w_chars, left, right):
        "internal function called by str_xstrip methods"
        value = self._val(space)
        chars = self._op_val(space, w_chars)

        lpos = 0
        rpos = len(value)

        if left:
            while lpos < rpos and value[lpos] in chars:
                lpos += 1

        if right:
            while rpos > lpos and value[rpos - 1] in chars:
                rpos -= 1

        assert rpos >= lpos    # annotator hint, don't remove
        return self._sliced(space, value, lpos, rpos, self)

    def _strip_none(self, space, left, right):
        "internal function called by str_xstrip methods"
        value = self._val(space)

        lpos = 0
        rpos = len(value)

        if left:
            while lpos < rpos and self._isspace(value[lpos]):
                lpos += 1

        if right:
            while rpos > lpos and self._isspace(value[rpos - 1]):
                rpos -= 1

        assert rpos >= lpos    # annotator hint, don't remove
        return self._sliced(space, value, lpos, rpos, self)

    def descr_strip(self, space, w_chars=None):
        if space.is_none(w_chars):
            return self._strip_none(space, left=1, right=1)
        return self._strip(space, w_chars, left=1, right=1)

    def descr_lstrip(self, space, w_chars=None):
        if space.is_none(w_chars):
            return self._strip_none(space, left=1, right=0)
        return self._strip(space, w_chars, left=1, right=0)

    def descr_rstrip(self, space, w_chars=None):
        if space.is_none(w_chars):
            return self._strip_none(space, left=0, right=1)
        return self._strip(space, w_chars, left=0, right=1)

    def descr_swapcase(self, space):
        selfvalue = self._val(space)
        builder = self._builder(len(selfvalue))
        for i in range(len(selfvalue)):
            ch = selfvalue[i]
            if self._isupper(ch):
                builder.append(self._lower(ch))
            elif self._islower(ch):
                builder.append(self._upper(ch))
            else:
                builder.append(ch)
        return self._new(builder.build())

    def descr_title(self, space):
        selfval = self._val(space)
        if len(selfval) == 0:
            return self
        return self._new(self.title(selfval))

    @jit.elidable
    def title(self, value):
        builder = self._builder(len(value))
        previous_is_cased = False
        for ch in value:
            if not previous_is_cased:
                builder.append(self._title(ch))
            else:
                builder.append(self._lower(ch))
            previous_is_cased = self._iscased(ch)
        return builder.build()

    DEFAULT_NOOP_TABLE = ''.join([chr(i) for i in range(256)])

    # for bytes and bytearray, overridden by unicode
    @unwrap_spec(w_deletechars=WrappedDefault(''))
    def descr_translate(self, space, w_table, w_deletechars):
        if space.is_w(w_table, space.w_None):
            table = self.DEFAULT_NOOP_TABLE
        else:
            table = self._op_val(space, w_table)
            if len(table) != 256:
                raise operationerrfmt(
                    space.w_ValueError,
                    "translation table must be 256 characters long")

        string = self._val(space)
        deletechars = self._op_val(space, w_deletechars)
        if len(deletechars) == 0:
            buf = self._builder(len(string))
            for char in string:
                buf.append(table[ord(char)])
        else:
            buf = self._builder()
            deletion_table = [False] * 256
            for c in deletechars:
                deletion_table[ord(c)] = True
            for char in string:
                if not deletion_table[ord(char)]:
                    buf.append(table[ord(char)])
        return self._new(buf.build())

    def descr_upper(self, space):
        value = self._val(space)
        builder = self._builder(len(value))
        for i in range(len(value)):
            builder.append(self._upper(value[i]))
        return self._new(builder.build())

    @unwrap_spec(width=int)
    def descr_zfill(self, space, width):
        selfval = self._val(space)
        if len(selfval) == 0:
            return self._new(self._chr('0') * width)
        num_zeros = width - len(selfval)
        if num_zeros <= 0:
            # cannot return self, in case it is a subclass of str
            return self._new(selfval)

        builder = self._builder(width)
        if len(selfval) > 0 and (selfval[0] == '+' or selfval[0] == '-'):
            # copy sign to first position
            builder.append(selfval[0])
            start = 1
        else:
            start = 0
        builder.append_multiple_char(self._chr('0'), num_zeros)
        builder.append_slice(selfval, start, len(selfval))
        return self._new(builder.build())

    def descr_getnewargs(self, space):
        return space.newtuple([self._new(self._val(space))])

# ____________________________________________________________
# helpers for slow paths, moved out because they contain loops

@specialize.argtype(0)
def _descr_getslice_slowpath(selfvalue, start, step, sl):
    return [selfvalue[start + i*step] for i in range(sl)]
