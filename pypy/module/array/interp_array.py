from rpython.rlib import jit, rgc
from rpython.rlib.buffer import Buffer
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import ovfcheck, widen
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.annlowlevel import llstr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.rstr import copy_string_to_raw

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, make_weakref_descr)
from pypy.module._file.interp_file import W_File


@unwrap_spec(typecode='text')
def w_array(space, w_cls, typecode, __args__):
    if len(__args__.arguments_w) > 1:
        raise oefmt(space.w_TypeError, "array() takes at most 2 arguments")
    if len(typecode) != 1:
        raise oefmt(space.w_TypeError,
                    "array() argument 1 must be char, not str")
    typecode = typecode[0]

    if space.is_w(w_cls, space.gettypeobject(W_ArrayBase.typedef)):
        if __args__.keywords:
            raise oefmt(space.w_TypeError,
                        "array.array() does not take keyword arguments")

    for tc in unroll_typecodes:
        if typecode == tc:
            a = space.allocate_instance(types[tc].w_class, w_cls)
            a.__init__(space)
            break
    else:
        raise oefmt(space.w_ValueError,
                    "bad typecode (must be c, b, B, u, h, H, i, I, l, L, f or "
                    "d)")

    if len(__args__.arguments_w) > 0:
        w_initializer = __args__.arguments_w[0]
        w_initializer_type = space.type(w_initializer)
        if w_initializer_type is space.w_bytes:
            a.descr_fromstring(space, w_initializer)
        elif w_initializer_type is space.w_list:
            a.descr_fromlist(space, w_initializer)
        else:
            a.extend(w_initializer, True)
    return a


def descr_itemsize(space, self):
    return space.newint(self.itemsize)


def descr_typecode(space, self):
    return space.newtext(self.typecode)

arr_eq_driver = jit.JitDriver(name='array_eq_driver', greens=['comp_func'],
                              reds='auto')
EQ, NE, LT, LE, GT, GE = range(6)

def compare_arrays(space, arr1, arr2, comp_op):
    if not (isinstance(arr1, W_ArrayBase) and isinstance(arr2, W_ArrayBase)):
        return space.w_NotImplemented
    if comp_op == EQ and arr1.len != arr2.len:
        return space.w_False
    if comp_op == NE and arr1.len != arr2.len:
        return space.w_True
    lgt = min(arr1.len, arr2.len)
    for i in range(lgt):
        arr_eq_driver.jit_merge_point(comp_func=comp_op)
        w_elem1 = arr1.w_getitem(space, i)
        w_elem2 = arr2.w_getitem(space, i)
        if comp_op == EQ:
            res = space.eq_w(w_elem1, w_elem2)
            if not res:
                return space.w_False
        elif comp_op == NE:
            res = space.is_true(space.ne(w_elem1, w_elem2))
            if res:
                return space.w_True
        elif comp_op == LT or comp_op == GT:
            if comp_op == LT:
                res = space.is_true(space.lt(w_elem1, w_elem2))
            else:
                res = space.is_true(space.gt(w_elem1, w_elem2))
            if res:
                return space.w_True
            elif not space.eq_w(w_elem1, w_elem2):
                return space.w_False
        else:
            if comp_op == LE:
                res = space.is_true(space.le(w_elem1, w_elem2))
            else:
                res = space.is_true(space.ge(w_elem1, w_elem2))
            if not res:
                return space.w_False
            elif not space.eq_w(w_elem1, w_elem2):
                return space.w_True
    # we have some leftovers
    if comp_op == EQ:
        return space.w_True
    elif comp_op == NE:
        return space.w_False
    if arr1.len == arr2.len:
        if comp_op == LT or comp_op == GT:
            return space.w_False
        return space.w_True
    if comp_op == LT or comp_op == LE:
        if arr1.len < arr2.len:
            return space.w_True
        return space.w_False
    if arr1.len > arr2.len:
        return space.w_True
    return space.w_False

UNICODE_ARRAY = lltype.Ptr(lltype.Array(lltype.UniChar,
                                        hints={'nolength': True}))

class W_ArrayBase(W_Root):
    _attrs_ = ('space', 'len', 'allocated', '_lifeline_', '_buffer')

    def __init__(self, space):
        self.space = space
        self.len = 0
        self.allocated = 0
        self._buffer = lltype.nullptr(rffi.CCHARP.TO)

    @rgc.must_be_light_finalizer
    def __del__(self):
        if self._buffer:
            lltype.free(self._buffer, flavor='raw')

    def setlen(self, size, zero=False, overallocate=True):
        if size > 0:
            if size > self.allocated or size < self.allocated / 2:
                if overallocate:
                    if size < 9:
                        some = 3
                    else:
                        some = 6
                    some += size >> 3
                else:
                    some = 0
                self.allocated = size + some
                byte_size = self.allocated * self.itemsize
                if zero:
                    new_buffer = lltype.malloc(
                        rffi.CCHARP.TO, byte_size, flavor='raw',
                        add_memory_pressure=True, zero=True)
                else:
                    new_buffer = lltype.malloc(
                        rffi.CCHARP.TO, byte_size, flavor='raw',
                        add_memory_pressure=True)
                    copy_bytes = min(size, self.len) * self.itemsize
                    rffi.c_memcpy(rffi.cast(rffi.VOIDP, new_buffer),
                                  rffi.cast(rffi.VOIDP, self._buffer),
                                  copy_bytes)
            else:
                self.len = size
                return
        else:
            assert size == 0
            self.allocated = 0
            new_buffer = lltype.nullptr(rffi.CCHARP.TO)

        if self._buffer:
            lltype.free(self._buffer, flavor='raw')
        self._buffer = new_buffer
        self.len = size

    def _fromiterable(self, w_seq):
        # used by fromsequence().
        # a more careful case if w_seq happens to be a very large
        # iterable: don't copy the items into some intermediate list
        w_iterator = self.space.iter(w_seq)
        tp = self.space.type(w_iterator)
        while True:
            unpack_driver.jit_merge_point(selfclass=self.__class__,
                                          tp=tp, self=self,
                                          w_iterator=w_iterator)
            space = self.space
            try:
                w_item = space.next(w_iterator)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break  # done
            self.descr_append(space, w_item)

    def _charbuf_start(self):
        return self._buffer

    def _buffer_as_unsigned(self):
        return rffi.cast(lltype.Unsigned, self._buffer)

    def _charbuf_stop(self):
        keepalive_until_here(self)

    def delitem(self, space, i, j):
        if i < 0:
            i += self.len
        if i < 0:
            i = 0
        if j < 0:
            j += self.len
        if j < 0:
            j = 0
        if j > self.len:
            j = self.len
        if i >= j:
            return None
        oldbuffer = self._buffer
        self._buffer = lltype.malloc(rffi.CCHARP.TO,
            (self.len - (j - i)) * self.itemsize, flavor='raw',
            add_memory_pressure=True)
        if i:
            rffi.c_memcpy(
                rffi.cast(rffi.VOIDP, self._buffer),
                rffi.cast(rffi.VOIDP, oldbuffer),
                i * self.itemsize
            )
        if j < self.len:
            rffi.c_memcpy(
                rffi.cast(rffi.VOIDP, rffi.ptradd(self._buffer,
                                                  i * self.itemsize)),
                rffi.cast(rffi.VOIDP, rffi.ptradd(oldbuffer,
                                                  j * self.itemsize)),
                (self.len - j) * self.itemsize
            )
        self.len -= j - i
        self.allocated = self.len
        if oldbuffer:
            lltype.free(oldbuffer, flavor='raw')

    def readbuf_w(self, space):
        return ArrayBuffer(self, True)

    def writebuf_w(self, space):
        return ArrayBuffer(self, False)

    def descr_append(self, space, w_x):
        """ append(x)

        Append new value x to the end of the array.
        """
        raise NotImplementedError

    def descr_extend(self, space, w_x):
        """ extend(array or iterable)

        Append items to the end of the array.
        """
        self.extend(w_x)

    def descr_count(self, space, w_val):
        """ count(x)

        Return number of occurrences of x in the array.
        """
        cnt = 0
        for i in range(self.len):
            # XXX jitdriver
            w_item = self.w_getitem(space, i)
            if space.eq_w(w_item, w_val):
                cnt += 1
        return space.newint(cnt)

    def descr_index(self, space, w_x):
        """ index(x)

        Return index of first occurrence of x in the array.
        """
        for i in range(self.len):
            w_item = self.w_getitem(space, i)
            if space.eq_w(w_item, w_x):
                return space.newint(i)
        raise oefmt(space.w_ValueError, "array.index(x): x not in list")

    def descr_reverse(self, space):
        """ reverse()

        Reverse the order of the items in the array.
        """
        raise NotImplementedError

    def descr_remove(self, space, w_val):
        """ remove(x)

        Remove the first occurrence of x in the array.
        """
        w_idx = self.descr_index(space, w_val)
        self.descr_pop(space, space.int_w(w_idx))

    @unwrap_spec(i=int)
    def descr_pop(self, space, i=-1):
        """ pop([i])

        Return the i-th element and delete it from the array. i defaults to -1.
        """
        raise NotImplementedError

    @unwrap_spec(idx=int)
    def descr_insert(self, space, idx, w_val):
        """ insert(i,x)

        Insert a new item x into the array before position i.
        """
        raise NotImplementedError

    def descr_tolist(self, space):
        """ tolist() -> list

        Convert array to an ordinary list with the same items.
        """
        w_l = space.newlist([])
        for i in range(self.len):
            w_l.append(self.w_getitem(space, i))
        return w_l

    def descr_fromlist(self, space, w_lst):
        """ fromlist(list)

        Append items to array from list.
        """
        if not space.isinstance_w(w_lst, space.w_list):
            raise oefmt(space.w_TypeError, "arg must be list")
        s = self.len
        try:
            self.fromsequence(w_lst)
        except OperationError:
            self.setlen(s)
            raise

    def descr_tostring(self, space):
        """ tostring() -> string

        Convert the array to an array of machine values and return the string
        representation.
        """
        size = self.len
        if size == 0:
            return space.newbytes('')
        cbuf = self._charbuf_start()
        s = rffi.charpsize2str(cbuf, size * self.itemsize)
        self._charbuf_stop()
        return self.space.newbytes(s)

    def descr_fromstring(self, space, w_s):
        """ fromstring(string)

        Appends items from the string, interpreting it as an array of machine
        values,as if it had been read from a file using the fromfile() method).
        """
        if self is w_s:
            raise oefmt(space.w_ValueError,
                        "array.fromstring(x): x cannot be self")
        s = space.getarg_w('s#', w_s)
        if len(s) % self.itemsize != 0:
            raise oefmt(self.space.w_ValueError,
                        "string length not a multiple of item size")
        oldlen = self.len
        new = len(s) / self.itemsize
        if not new:
            return
        self.setlen(oldlen + new)
        cbuf = self._charbuf_start()
        copy_string_to_raw(llstr(s), rffi.ptradd(cbuf, oldlen * self.itemsize),
                           0, len(s))
        self._charbuf_stop()

    @unwrap_spec(w_f=W_File, n=int)
    def descr_fromfile(self, space, w_f, n):
        """ fromfile(f, n)

        Read n objects from the file object f and append them to the end of the
        array.  Also called as read.
        """
        try:
            size = ovfcheck(self.itemsize * n)
        except OverflowError:
            raise MemoryError
        w_item = space.call_method(w_f, 'read', space.newint(size))
        item = space.bytes_w(w_item)
        if len(item) < size:
            n = len(item) % self.itemsize
            elems = max(0, len(item) - (len(item) % self.itemsize))
            if n != 0:
                item = item[0:elems]
            self.descr_fromstring(space, space.newbytes(item))
            raise oefmt(space.w_EOFError, "not enough items in file")
        self.descr_fromstring(space, w_item)

    @unwrap_spec(w_f=W_File)
    def descr_tofile(self, space, w_f):
        """ tofile(f)

        Write all items (as machine values) to the file object f.  Also
        called as write.
        """
        w_s = self.descr_tostring(space)
        space.call_method(w_f, 'write', w_s)

    def descr_fromunicode(self, space, w_ustr):
        """ fromunicode(ustr)

        Extends this array with data from the unicode string ustr.
        The array must be a type 'u' array; otherwise a ValueError
        is raised.  Use array.fromstring(ustr.decode(...)) to
        append Unicode data to an array of some other type.
        """
        # XXX the following probable bug is not emulated:
        # CPython accepts a non-unicode string or a buffer, and then
        # behaves just like fromstring(), except that it strangely truncate
        # string arguments at multiples of the unicode byte size.
        # Let's only accept unicode arguments for now.
        if self.typecode == 'u':
            self.fromsequence(w_ustr)
        else:
            raise oefmt(space.w_ValueError,
                        "fromunicode() may only be called on type 'u' arrays")

    def descr_tounicode(self, space):
        """ tounicode() -> unicode

        Convert the array to a unicode string.  The array must be
        a type 'u' array; otherwise a ValueError is raised.  Use
        array.tostring().decode() to obtain a unicode string from
        an array of some other type.
        """
        if self.typecode == 'u':
            buf = rffi.cast(UNICODE_ARRAY, self._buffer_as_unsigned())
            return space.newunicode(rffi.wcharpsize2unicode(buf, self.len))
        else:
            raise oefmt(space.w_ValueError,
                        "tounicode() may only be called on type 'u' arrays")

    def descr_buffer_info(self, space):
        """ buffer_info() -> (address, length)

        Return a tuple (address, length) giving the current memory address and
        the length in items of the buffer used to hold array's contents
        The length should be multiplied by the itemsize attribute to calculate
        the buffer length in bytes.
        """
        w_ptr = space.newint(self._buffer_as_unsigned())
        w_len = space.newint(self.len)
        return space.newtuple([w_ptr, w_len])

    def descr_reduce(self, space):
        """ Return state information for pickling.
        """
        if self.len > 0:
            w_s = self.descr_tostring(space)
            args = [space.newtext(self.typecode), w_s]
        else:
            args = [space.newtext(self.typecode)]
        try:
            w_dict = space.getattr(self, space.newtext('__dict__'))
        except OperationError:
            w_dict = space.w_None
        return space.newtuple([space.type(self), space.newtuple(args), w_dict])

    def descr_copy(self, space):
        """ copy(array)

        Return a copy of the array.
        """
        w_a = self.constructor(self.space)
        w_a.setlen(self.len, overallocate=False)
        rffi.c_memcpy(
            rffi.cast(rffi.VOIDP, w_a._buffer_as_unsigned()),
            rffi.cast(rffi.VOIDP, self._buffer_as_unsigned()),
            self.len * self.itemsize
        )
        return w_a

    def descr_byteswap(self, space):
        """ byteswap()

        Byteswap all items of the array.  If the items in the array are
        not 1, 2, 4, or 8 bytes in size, RuntimeError is raised.
        """
        if self.itemsize not in [1, 2, 4, 8]:
            raise oefmt(space.w_RuntimeError,
                        "byteswap not supported for this array")
        if self.len == 0:
            return
        bytes = self._charbuf_start()
        tmp = [bytes[0]] * self.itemsize
        for start in range(0, self.len * self.itemsize, self.itemsize):
            stop = start + self.itemsize - 1
            for i in range(self.itemsize):
                tmp[i] = bytes[start + i]
            for i in range(self.itemsize):
                bytes[stop - i] = tmp[i]
        self._charbuf_stop()

    def descr_len(self, space):
        return space.newint(self.len)

    def descr_eq(self, space, w_arr2):
        "x.__eq__(y) <==> x==y"
        return compare_arrays(space, self, w_arr2, EQ)

    def descr_ne(self, space, w_arr2):
        "x.__ne__(y) <==> x!=y"
        return compare_arrays(space, self, w_arr2, NE)

    def descr_lt(self, space, w_arr2):
        "x.__lt__(y) <==> x<y"
        return compare_arrays(space, self, w_arr2, LT)

    def descr_le(self, space, w_arr2):
        "x.__le__(y) <==> x<=y"
        return compare_arrays(space, self, w_arr2, LE)

    def descr_gt(self, space, w_arr2):
        "x.__gt__(y) <==> x>y"
        return compare_arrays(space, self, w_arr2, GT)

    def descr_ge(self, space, w_arr2):
        "x.__ge__(y) <==> x>=y"
        return compare_arrays(space, self, w_arr2, GE)

    # Basic get/set/append/extend methods

    def descr_getitem(self, space, w_idx):
        "x.__getitem__(y) <==> x[y]"
        if not space.isinstance_w(w_idx, space.w_slice):
            idx, stop, step = space.decode_index(w_idx, self.len)
            assert step == 0
            return self.w_getitem(space, idx)
        else:
            return self.getitem_slice(space, w_idx)

    def descr_getslice(self, space, w_i, w_j):
        return space.getitem(self, space.newslice(w_i, w_j, space.w_None))

    def descr_setitem(self, space, w_idx, w_item):
        "x.__setitem__(i, y) <==> x[i]=y"
        if space.isinstance_w(w_idx, space.w_slice):
            self.setitem_slice(space, w_idx, w_item)
        else:
            self.setitem(space, w_idx, w_item)

    def descr_setslice(self, space, w_start, w_stop, w_item):
        self.setitem_slice(space,
                           space.newslice(w_start, w_stop, space.w_None),
                           w_item)

    def descr_delitem(self, space, w_idx):
        start, stop, step, size = self.space.decode_index4(w_idx, self.len)
        if step != 1:
            # I don't care about efficiency of that so far
            w_lst = self.descr_tolist(space)
            space.delitem(w_lst, w_idx)
            self.setlen(0)
            self.fromsequence(w_lst)
            return
        return self.delitem(space, start, stop)

    def descr_delslice(self, space, w_start, w_stop):
        self.descr_delitem(space, space.newslice(w_start, w_stop,
                                                 space.w_None))

    def descr_iter(self, space):
        return space.newseqiter(self)

    def descr_add(self, space, w_other):
        if (not isinstance(w_other, W_ArrayBase)
                or w_other.typecode != self.typecode):
            return space.w_NotImplemented
        a = self.constructor(space)
        a.setlen(self.len + w_other.len, overallocate=False)
        if self.len:
            rffi.c_memcpy(
                rffi.cast(rffi.VOIDP, a._buffer),
                rffi.cast(rffi.VOIDP, self._buffer),
                self.len * self.itemsize
            )
        if w_other.len:
            rffi.c_memcpy(
                rffi.cast(rffi.VOIDP, rffi.ptradd(a._buffer,
                                             self.len * self.itemsize)),
                rffi.cast(rffi.VOIDP, w_other._buffer),
                w_other.len * self.itemsize
            )
        keepalive_until_here(self)
        keepalive_until_here(a)
        return a

    def descr_inplace_add(self, space, w_other):
        if (not isinstance(w_other, W_ArrayBase)
                or w_other.typecode != self.typecode):
            return space.w_NotImplemented
        oldlen = self.len
        otherlen = w_other.len
        self.setlen(oldlen + otherlen)
        if otherlen:
            rffi.c_memcpy(
                rffi.cast(rffi.VOIDP, rffi.ptradd(self._buffer,
                                             oldlen * self.itemsize)),
                rffi.cast(rffi.VOIDP, w_other._buffer),
                otherlen * self.itemsize
            )
        keepalive_until_here(self)
        keepalive_until_here(w_other)
        return self

    def _mul_helper(self, space, w_repeat, is_inplace):
        try:
            repeat = space.getindex_w(w_repeat, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        if is_inplace:
            a = self
            start = 1
        else:
            a = self.constructor(space)
            start = 0
        if repeat <= start:
            if repeat <= 0:
                a.setlen(0, overallocate=False)
            return a
        oldlen = self.len
        try:
            newlen = ovfcheck(oldlen * repeat)
        except OverflowError:
            raise MemoryError
        #
        srcbuf = self._buffer
        srcsize = self.len * self.itemsize
        for i in range(srcsize):
            if srcbuf[i] != '\x00':
                break
        else:
            # the source is entirely zero: initialize the target
            # with zeroes too
            a.setlen(newlen, zero=True, overallocate=False)
            return a
        #
        a.setlen(newlen, overallocate=False)
        srcbuf = self._buffer   # reload this, in case self is a
        if oldlen == 1:
            self._repeat_single_item(a, start, repeat)
        else:
            dstbuf = a._buffer
            if start == 1:
                dstbuf = rffi.ptradd(dstbuf, srcsize)
            for r in range(start, repeat):
                rffi.c_memcpy(rffi.cast(rffi.VOIDP, dstbuf),
                              rffi.cast(rffi.VOIDP, srcbuf),
                              srcsize)
                dstbuf = rffi.ptradd(dstbuf, srcsize)
        keepalive_until_here(self)
        keepalive_until_here(a)
        return a

    def descr_mul(self, space, w_repeat):
        return self._mul_helper(space, w_repeat, False)

    def descr_inplace_mul(self, space, w_repeat):
        return self._mul_helper(space, w_repeat, True)

    def descr_radd(self, space, w_other):
        return self.descr_add(space, w_other)

    def descr_rmul(self, space, w_repeat):
        return self.descr_mul(space, w_repeat)

    # Misc methods

    def descr_repr(self, space):
        if self.len == 0:
            return space.newtext("array('%s')" % self.typecode)
        elif self.typecode == "c":
            r = space.repr(self.descr_tostring(space))
            s = "array('%s', %s)" % (self.typecode, space.text_w(r))
            return space.newtext(s)
        elif self.typecode == "u":
            r = space.repr(self.descr_tounicode(space))
            s = "array('%s', %s)" % (self.typecode, space.text_w(r))
            return space.newtext(s)
        else:
            r = space.repr(self.descr_tolist(space))
            s = "array('%s', %s)" % (self.typecode, space.text_w(r))
            return space.newtext(s)

W_ArrayBase.typedef = TypeDef(
    'array.array',
    __new__ = interp2app(w_array),

    __len__ = interp2app(W_ArrayBase.descr_len),
    __eq__ = interp2app(W_ArrayBase.descr_eq),
    __ne__ = interp2app(W_ArrayBase.descr_ne),
    __lt__ = interp2app(W_ArrayBase.descr_lt),
    __le__ = interp2app(W_ArrayBase.descr_le),
    __gt__ = interp2app(W_ArrayBase.descr_gt),
    __ge__ = interp2app(W_ArrayBase.descr_ge),

    __getitem__ = interp2app(W_ArrayBase.descr_getitem),
    __getslice__ = interp2app(W_ArrayBase.descr_getslice),
    __setitem__ = interp2app(W_ArrayBase.descr_setitem),
    __setslice__ = interp2app(W_ArrayBase.descr_setslice),
    __delitem__ = interp2app(W_ArrayBase.descr_delitem),
    __delslice__ = interp2app(W_ArrayBase.descr_delslice),
    __iter__ = interp2app(W_ArrayBase.descr_iter),

    __add__ = interpindirect2app(W_ArrayBase.descr_add),
    __iadd__ = interpindirect2app(W_ArrayBase.descr_inplace_add),
    __mul__ = interpindirect2app(W_ArrayBase.descr_mul),
    __imul__ = interpindirect2app(W_ArrayBase.descr_inplace_mul),
    __radd__ = interp2app(W_ArrayBase.descr_radd),
    __rmul__ = interp2app(W_ArrayBase.descr_rmul),

    __repr__ = interp2app(W_ArrayBase.descr_repr),

    itemsize = GetSetProperty(descr_itemsize),
    typecode = GetSetProperty(descr_typecode),
    __weakref__ = make_weakref_descr(W_ArrayBase),
    append = interpindirect2app(W_ArrayBase.descr_append),
    extend = interp2app(W_ArrayBase.descr_extend),
    count = interpindirect2app(W_ArrayBase.descr_count),
    index = interpindirect2app(W_ArrayBase.descr_index),
    reverse = interpindirect2app(W_ArrayBase.descr_reverse),
    remove = interpindirect2app(W_ArrayBase.descr_remove),
    pop = interpindirect2app(W_ArrayBase.descr_pop),
    insert = interpindirect2app(W_ArrayBase.descr_insert),

    tolist = interp2app(W_ArrayBase.descr_tolist),
    fromlist = interp2app(W_ArrayBase.descr_fromlist),
    tostring = interp2app(W_ArrayBase.descr_tostring),
    fromstring = interp2app(W_ArrayBase.descr_fromstring),
    tofile = interp2app(W_ArrayBase.descr_tofile),
    fromfile = interp2app(W_ArrayBase.descr_fromfile),
    fromunicode = interp2app(W_ArrayBase.descr_fromunicode),
    tounicode = interp2app(W_ArrayBase.descr_tounicode),

    buffer_info = interp2app(W_ArrayBase.descr_buffer_info),
    __copy__ = interp2app(W_ArrayBase.descr_copy),
    __reduce__ = interp2app(W_ArrayBase.descr_reduce),
    byteswap = interp2app(W_ArrayBase.descr_byteswap),
)


class TypeCode(object):
    def __init__(self, itemtype, unwrap, canoverflow=False, signed=False,
                 method='__int__'):
        self.itemtype = itemtype
        self.bytes = rffi.sizeof(itemtype)
        self.arraytype = lltype.Array(itemtype, hints={'nolength': True})
        self.arrayptrtype = lltype.Ptr(self.arraytype)
        self.unwrap = unwrap
        self.signed = signed
        self.canoverflow = canoverflow
        self.w_class = None
        self.method = method

    def _freeze_(self):
        # hint for the annotator: track individual constant instances
        return True

if rffi.sizeof(rffi.UINT) == rffi.sizeof(rffi.ULONG):
    # 32 bits: UINT can't safely overflow into a C long (rpython int)
    # via int_w, handle it like ULONG below
    _UINTTypeCode = \
         TypeCode(rffi.UINT,          'bigint_w')
else:
    _UINTTypeCode = \
         TypeCode(rffi.UINT,          'int_w', True)
types = {
    'c': TypeCode(lltype.Char,        'bytes_w', method=''),
    'u': TypeCode(lltype.UniChar,     'unicode_w', method=''),
    'b': TypeCode(rffi.SIGNEDCHAR,    'int_w', True, True),
    'B': TypeCode(rffi.UCHAR,         'int_w', True),
    'h': TypeCode(rffi.SHORT,         'int_w', True, True),
    'H': TypeCode(rffi.USHORT,        'int_w', True),
    'i': TypeCode(rffi.INT,           'int_w', True, True),
    'I': _UINTTypeCode,
    'l': TypeCode(rffi.LONG,          'int_w', True, True),
    'L': TypeCode(rffi.ULONG,         'bigint_w'),  # Overflow handled by
                                                    # rbigint.touint() which
                                                    # corresponds to the
                                                    # C-type unsigned long
    'f': TypeCode(lltype.SingleFloat, 'float_w', method='__float__'),
    'd': TypeCode(lltype.Float,       'float_w', method='__float__'),
    }
for k, v in types.items():
    v.typecode = k
unroll_typecodes = unrolling_iterable(types.keys())

class ArrayBuffer(Buffer):
    _immutable_ = True

    def __init__(self, array, readonly):
        self.array = array
        self.readonly = readonly

    def getlength(self):
        return self.array.len * self.array.itemsize

    def getformat(self):
        return self.array.typecode

    def getitemsize(self):
        return self.array.itemsize

    def getndim(self):
        return 1

    def getstrides(self):
        return [self.getitemsize()]

    def getitem(self, index):
        array = self.array
        data = array._charbuf_start()
        char = data[index]
        array._charbuf_stop()
        return char

    def setitem(self, index, char):
        array = self.array
        data = array._charbuf_start()
        data[index] = char
        array._charbuf_stop()

    def getslice(self, start, stop, step, size):
        if size == 0:
            return ''
        if step == 1:
            data = self.array._charbuf_start()
            try:
                return rffi.charpsize2str(rffi.ptradd(data, start), size)
            finally:
                self.array._charbuf_stop()
        return Buffer.getslice(self, start, stop, step, size)

    def get_raw_address(self):
        return self.array._charbuf_start()


unpack_driver = jit.JitDriver(name='unpack_array',
                              greens=['selfclass', 'tp'],
                              reds=['self', 'w_iterator'])

def make_array(mytype):
    W_ArrayBase = globals()['W_ArrayBase']

    class W_Array(W_ArrayBase):
        itemsize = mytype.bytes
        typecode = mytype.typecode

        _attrs_ = W_ArrayBase._attrs_

        def get_buffer(self):
            return rffi.cast(mytype.arrayptrtype, self._buffer)

        def item_w(self, w_item):
            space = self.space
            unwrap = getattr(space, mytype.unwrap)
            try:
                item = unwrap(w_item)
            except OperationError as e:
                if space.isinstance_w(w_item, space.w_float):
                    # Odd special case from cpython
                    raise
                if mytype.method != '' and e.match(space, space.w_TypeError):
                    try:
                        item = unwrap(space.call_method(w_item, mytype.method))
                    except OperationError:
                        raise oefmt(space.w_TypeError,
                                    "array item must be " + mytype.unwrap[:-2])
                else:
                    raise
            if mytype.unwrap == 'bigint_w':
                try:
                    item = item.touint()
                except (ValueError, OverflowError):
                    raise oefmt(space.w_OverflowError,
                                "unsigned %d-byte integer out of range",
                                mytype.bytes)
                return rffi.cast(mytype.itemtype, item)
            if mytype.unwrap == 'bytes_w' or mytype.unwrap == 'unicode_w':
                if len(item) != 1:
                    raise oefmt(space.w_TypeError, "array item must be char")
                item = item[0]
                return rffi.cast(mytype.itemtype, item)
            #
            # "regular" case: it fits in an rpython integer (lltype.Signed)
            # or it is a float
            return self.item_from_int_or_float(item)

        def item_from_int_or_float(self, item):
            result = rffi.cast(mytype.itemtype, item)
            if mytype.canoverflow:
                if rffi.cast(lltype.Signed, result) != item:
                    # overflow.  build the correct message
                    if item < 0:
                        msg = ('signed %d-byte integer is less than minimum' %
                               mytype.bytes)
                    else:
                        msg = ('signed %d-byte integer is greater than maximum'
                               % mytype.bytes)
                    if not mytype.signed:
                        msg = 'un' + msg      # 'signed' => 'unsigned'
                    raise OperationError(self.space.w_OverflowError,
                                         self.space.newtext(msg))
            return result

        def fromsequence(self, w_seq):
            space = self.space
            oldlen = self.len
            newlen = oldlen

            # optimized case for arrays of integers or floats
            if mytype.unwrap == 'int_w':
                lst = space.listview_int(w_seq)
            elif mytype.unwrap == 'float_w':
                lst = space.listview_float(w_seq)
            else:
                lst = None
            if lst is not None:
                self.setlen(oldlen + len(lst))
                try:
                    buf = self.get_buffer()
                    for num in lst:
                        buf[newlen] = self.item_from_int_or_float(num)
                        newlen += 1
                except OperationError:
                    self.setlen(newlen)
                    raise
                keepalive_until_here(self)
                return

            # this is the common case: w_seq is a list or a tuple
            lst_w = space.listview_no_unpack(w_seq)
            if lst_w is not None:
                self.setlen(oldlen + len(lst_w))
                buf = self.get_buffer()
                try:
                    for w_num in lst_w:
                        # note: self.item_w() might invoke arbitrary code.
                        # In case it resizes the same array, then strange
                        # things may happen, but as we don't reload 'buf'
                        # we know that one is big enough for all items
                        # (so at least we avoid crashes)
                        buf[newlen] = self.item_w(w_num)
                        newlen += 1
                except OperationError:
                    if buf == self.get_buffer():
                        self.setlen(newlen)
                    raise
                keepalive_until_here(self)
                return

            self._fromiterable(w_seq)

        def extend(self, w_iterable, accept_different_array=False):
            space = self.space
            if isinstance(w_iterable, W_Array):
                oldlen = self.len
                new = w_iterable.len
                self.setlen(self.len + new)
                i = 0
                buf = self.get_buffer()
                srcbuf = w_iterable.get_buffer()
                while i < new:
                    if oldlen + i >= self.len:
                        self.setlen(oldlen + i + 1)
                    buf[oldlen + i] = srcbuf[i]
                    i += 1
                keepalive_until_here(w_iterable)
                self.setlen(oldlen + i)
            elif (not accept_different_array
                  and isinstance(w_iterable, W_ArrayBase)):
                raise oefmt(space.w_TypeError,
                            "can only extend with array of same kind")
            else:
                self.fromsequence(w_iterable)

        def w_getitem(self, space, idx):
            item = self.get_buffer()[idx]
            keepalive_until_here(self)
            if mytype.typecode in 'bBhHil':
                item = rffi.cast(lltype.Signed, item)
                return space.newint(item)
            if mytype.typecode in 'IL':
                return space.newint(item)
            elif mytype.typecode in 'fd':
                item = float(item)
                return space.newfloat(item)
            elif mytype.typecode == 'c':
                return space.newbytes(item)
            elif mytype.typecode == 'u':
                return space.newunicode(item)
            assert 0, "unreachable"

        # interface

        def descr_append(self, space, w_x):
            x = self.item_w(w_x)
            index = self.len
            self.setlen(index + 1)
            self.get_buffer()[index] = x
            keepalive_until_here(self)

        # List interface

        def descr_reverse(self, space):
            b = self.get_buffer()
            for i in range(self.len / 2):
                b[i], b[self.len - i - 1] = b[self.len - i - 1], b[i]
            keepalive_until_here(self)

        def descr_pop(self, space, i):
            if i < 0:
                i += self.len
            if i < 0 or i >= self.len:
                raise oefmt(space.w_IndexError, "pop index out of range")
            w_val = self.w_getitem(space, i)
            b = self.get_buffer()
            while i < self.len - 1:
                b[i] = b[i + 1]
                i += 1
            keepalive_until_here(self)
            self.setlen(self.len - 1)
            return w_val

        def descr_insert(self, space, idx, w_val):
            if idx < 0:
                idx += self.len
            if idx < 0:
                idx = 0
            if idx > self.len:
                idx = self.len

            val = self.item_w(w_val)
            self.setlen(self.len + 1)
            i = self.len - 1
            b = self.get_buffer()
            while i > idx:
                b[i] = b[i - 1]
                i -= 1
            b[i] = val
            keepalive_until_here(self)

        def getitem_slice(self, space, w_idx):
            start, stop, step, size = space.decode_index4(w_idx, self.len)
            w_a = mytype.w_class(self.space)
            w_a.setlen(size, overallocate=False)
            assert step != 0
            j = 0
            buf = w_a.get_buffer()
            srcbuf = self.get_buffer()
            for i in range(start, stop, step):
                buf[j] = srcbuf[i]
                j += 1
            keepalive_until_here(self)
            keepalive_until_here(w_a)
            return w_a

        def setitem(self, space, w_idx, w_item):
            idx, stop, step = space.decode_index(w_idx, self.len)
            if step != 0:
                raise oefmt(self.space.w_TypeError,
                            "can only assign array to array slice")
            item = self.item_w(w_item)
            self.get_buffer()[idx] = item
            keepalive_until_here(self)

        def setitem_slice(self, space, w_idx, w_item):
            if not isinstance(w_item, W_Array):
                raise oefmt(space.w_TypeError,
                            "can only assign to a slice array")
            start, stop, step, size = self.space.decode_index4(w_idx, self.len)
            assert step != 0
            if w_item.len != size or self is w_item:
                # XXX this is a giant slow hack
                w_lst = self.descr_tolist(space)
                w_item = space.call_method(w_item, 'tolist')
                space.setitem(w_lst, w_idx, w_item)
                self.setlen(0)
                self.fromsequence(w_lst)
            else:
                j = 0
                buf = self.get_buffer()
                srcbuf = w_item.get_buffer()
                for i in range(start, stop, step):
                    buf[i] = srcbuf[j]
                    j += 1
                keepalive_until_here(w_item)
                keepalive_until_here(self)

        def _repeat_single_item(self, a, start, repeat):
            # <a performance hack>
            assert isinstance(a, W_Array)
            item = self.get_buffer()[0]
            dstbuf = a.get_buffer()
            for r in range(start, repeat):
                dstbuf[r] = item

    mytype.w_class = W_Array
    W_Array.constructor = W_Array
    name = 'ArrayType' + mytype.typecode
    W_Array.__name__ = 'W_' + name

for mytype in types.values():
    make_array(mytype)
del mytype
