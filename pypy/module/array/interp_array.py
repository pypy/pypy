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


@unwrap_spec(typecode=str)
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
                    "bad typecode (must be b, B, u, h, H, i, I, l, L, q, Q, f "
                    "or d)")

    if len(__args__.arguments_w) > 0:
        w_initializer = __args__.arguments_w[0]
        if tc != 'u':
            if space.isinstance_w(w_initializer, space.w_unicode):
                raise oefmt(
                    space.w_TypeError,
                    "cannot use a str to initialize an array with "
                    "typecode '%s'", tc)
            elif (isinstance(w_initializer, W_ArrayBase)
                    and w_initializer.typecode == 'u'):
                raise oefmt(
                    space.w_TypeError,
                    "cannot use a unicode array to initialize an array with "
                    "typecode '%s'", tc)
        if isinstance(w_initializer, W_ArrayBase):
            a.extend(w_initializer, True)
        elif space.type(w_initializer) is space.w_list:
            a.descr_fromlist(space, w_initializer)
        else:
            try:
                buf = space.bufferstr_w(w_initializer)
            except OperationError as e:
                if not e.match(space, space.w_TypeError):
                    raise
                a.extend(w_initializer, True)
            else:
                a._frombytes(space, buf)
    return a


def descr_itemsize(space, self):
    assert isinstance(self, W_ArrayBase)
    return space.wrap(self.itemsize)


def descr_typecode(space, self):
    assert isinstance(self, W_ArrayBase)
    return space.wrap(self.typecode)

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
            res = space.is_true(space.eq(w_elem1, w_elem2))
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
            elif not space.is_true(space.eq(w_elem1, w_elem2)):
                return space.w_False
        else:
            if comp_op == LE:
                res = space.is_true(space.le(w_elem1, w_elem2))
            else:
                res = space.is_true(space.ge(w_elem1, w_elem2))
            if not res:
                return space.w_False
            elif not space.is_true(space.eq(w_elem1, w_elem2)):
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
    _attrs_ = ('space', 'len', 'allocated', '_lifeline_') # no buffer

    def __init__(self, space):
        self.space = space
        self.len = 0
        self.allocated = 0

    def buffer_w_ex(self, space, flags):
        return ArrayBuffer(self, False), self.typecode, self.itemsize

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
        raise NotImplementedError

    def descr_index(self, space, w_x):
        """ index(x)

        Return index of first occurrence of x in the array.
        """
        raise NotImplementedError

    def descr_reverse(self, space):
        """ reverse()

        Reverse the order of the items in the array.
        """
        raise NotImplementedError

    def descr_remove(self, space, w_val):
        """ remove(x)

        Remove the first occurrence of x in the array.
        """
        raise NotImplementedError

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
        """ tostring() -> bytes

        Convert the array to an array of machine values and return the
        bytes representation.

        This method is deprecated. Use tobytes instead.
        """
        msg = "tostring() is deprecated. Use tobytes() instead."
        space.warn(space.wrap(msg), space.w_DeprecationWarning)
        return self.descr_tobytes(space)

    def descr_tobytes(self, space):
        """tobytes() -> bytes

        Convert the array to an array of machine values and return the
        bytes representation.
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

        Appends items from the string, interpreting it as an array of
        machine values, as if it had been read from a file using the
        fromfile() method).

        This method is deprecated. Use frombytes instead.
        """
        if self is w_s:
            raise oefmt(space.w_ValueError,
                        "array.fromstring(x): x cannot be self")
        s = space.getarg_w('s#', w_s)
        msg = "fromstring() is deprecated. Use frombytes() instead."
        space.warn(space.wrap(msg), self.space.w_DeprecationWarning)
        self._frombytes(space, s)

    def descr_frombytes(self, space, w_s):
        """frombytes(bytestring)

        Appends items from the string, interpreting it as an array of
        machine values, as if it had been read from a file using the
        fromfile() method).
        """
        buf = space.getarg_w('y*', w_s)
        if buf.getitemsize() != 1:
            raise oefmt(space.w_TypeError, "a bytes-like object is required")
        s = buf.as_str()
        self._frombytes(space, s)

    def _frombytes(self, space, s):
        if len(s) % self.itemsize != 0:
            raise oefmt(space.w_ValueError,
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

    @unwrap_spec(n=int)
    def descr_fromfile(self, space, w_f, n):
        """ fromfile(f, n)

        Read n objects from the file object f and append them to the end of the
        array.
        """
        try:
            size = ovfcheck(self.itemsize * n)
        except OverflowError:
            raise MemoryError
        w_item = space.call_method(w_f, 'read', space.wrap(size))
        item = space.bytes_w(w_item)
        if len(item) < size:
            n = len(item) % self.itemsize
            elems = max(0, len(item) - (len(item) % self.itemsize))
            if n != 0:
                item = item[0:elems]
            self._frombytes(space, item)
            raise oefmt(space.w_EOFError, "not enough items in file")
        self._frombytes(space, item)

    def descr_tofile(self, space, w_f):
        """ tofile(f)

        Write all items (as machine values) to the file object f.  Also
        called as write.
        """
        w_s = self.descr_tobytes(space)
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
            return space.wrap(rffi.wcharpsize2unicode(buf, self.len))
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
        w_ptr = space.wrap(self._buffer_as_unsigned())
        w_len = space.wrap(self.len)
        return space.newtuple([w_ptr, w_len])

    @unwrap_spec(protocol=int)
    def descr_reduce_ex(self, space, protocol):
        """Return state information for pickling."""
        try:
            w_dict = space.getattr(self, space.wrap('__dict__'))
        except OperationError:
            w_dict = space.w_None
        from pypy.module.array import reconstructor
        mformat_code = reconstructor.typecode_to_mformat_code(self.typecode)
        if protocol < 3 or mformat_code == reconstructor.UNKNOWN_FORMAT:
            # Convert the array to a list if we got something weird
            # (e.g., non-IEEE floats), or we are pickling the array
            # using a Python 2.x compatible protocol.
            #
            # It is necessary to use a list representation for Python
            # 2.x compatible pickle protocol, since Python 2's str
            # objects are unpickled as unicode by Python 3. Thus it is
            # impossible to make arrays unpicklable by Python 3 by
            # using their memory representation, unless we resort to
            # ugly hacks such as coercing unicode objects to bytes in
            # array_reconstructor.
            w_list = self.descr_tolist(space)
            return space.newtuple([
                    space.type(self),
                    space.newtuple([space.wrap(self.typecode), w_list]),
                    w_dict])

        w_bytes = self.descr_tobytes(space)
        w_array_reconstructor = space.fromcache(State).w_array_reconstructor
        return space.newtuple([
                w_array_reconstructor,
                space.newtuple([space.type(self),
                                space.wrap(self.typecode),
                                space.wrap(mformat_code),
                                w_bytes]),
                w_dict])

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
        return space.wrap(self.len)

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

    def descr_setitem(self, space, w_idx, w_item):
        "x.__setitem__(i, y) <==> x[i]=y"
        if space.isinstance_w(w_idx, space.w_slice):
            self.setitem_slice(space, w_idx, w_item)
        else:
            self.setitem(space, w_idx, w_item)

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

    def descr_iter(self, space):
        return space.newseqiter(self)

    def descr_add(self, space, w_other):
        raise NotImplementedError

    def descr_inplace_add(self, space, w_other):
        raise NotImplementedError

    def descr_mul(self, space, w_repeat):
        raise NotImplementedError

    def descr_inplace_mul(self, space, w_repeat):
        raise NotImplementedError

    def descr_radd(self, space, w_other):
        return self.descr_add(space, w_other)

    def descr_rmul(self, space, w_repeat):
        return self.descr_mul(space, w_repeat)

    # Misc methods

    def descr_repr(self, space):
        if self.len == 0:
            return space.wrap("array('%s')" % self.typecode)
        elif self.typecode == "u":
            r = space.repr(self.descr_tounicode(space))
            s = u"array('u', %s)" % space.unicode_w(r)
            return space.wrap(s)
        else:
            r = space.repr(self.descr_tolist(space))
            s = "array('%s', %s)" % (self.typecode, space.str_w(r))
            return space.wrap(s)

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
    __setitem__ = interp2app(W_ArrayBase.descr_setitem),
    __delitem__ = interp2app(W_ArrayBase.descr_delitem),
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
    tobytes = interp2app(W_ArrayBase.descr_tobytes),
    frombytes = interp2app(W_ArrayBase.descr_frombytes),

    buffer_info = interp2app(W_ArrayBase.descr_buffer_info),
    __copy__ = interp2app(W_ArrayBase.descr_copy),
    __reduce_ex__ = interp2app(W_ArrayBase.descr_reduce_ex),
    byteswap = interp2app(W_ArrayBase.descr_byteswap),
)


class TypeCode(object):
    def __init__(self, itemtype, unwrap, canoverflow=False, signed=False,
                 method='__int__'):
        self.itemtype = itemtype
        self.bytes = rffi.sizeof(itemtype)
        self.arraytype = lltype.Array(itemtype, hints={'nolength': True})
        self.unwrap, _, self.convert = unwrap.partition('.')
        self.signed = signed
        self.canoverflow = canoverflow
        self.w_class = None
        self.method = method

    def _freeze_(self):
        # hint for the annotator: track individual constant instances
        return True

    def is_integer_type(self):
        return self.unwrap == 'int_w' or self.unwrap == 'bigint_w'


if rffi.sizeof(rffi.UINT) == rffi.sizeof(rffi.ULONG):
    # 32 bits: UINT can't safely overflow into a C long (rpython int)
    # via int_w, handle it like ULONG below
    _UINTTypeCode = \
         TypeCode(rffi.UINT,          'bigint_w.touint')
else:
    _UINTTypeCode = \
         TypeCode(rffi.UINT,          'int_w', True)
types = {
    'u': TypeCode(lltype.UniChar,     'unicode_w', method=''),
    'b': TypeCode(rffi.SIGNEDCHAR,    'int_w', True, True),
    'B': TypeCode(rffi.UCHAR,         'int_w', True),
    'h': TypeCode(rffi.SHORT,         'int_w', True, True),
    'H': TypeCode(rffi.USHORT,        'int_w', True),
    'i': TypeCode(rffi.INT,           'int_w', True, True),
    'I': _UINTTypeCode,
    'l': TypeCode(rffi.LONG,          'int_w', True, True),
    'L': TypeCode(rffi.ULONG,         'bigint_w.touint'),
    'q': TypeCode(rffi.LONGLONG,      'bigint_w.tolonglong', True, True),
    'Q': TypeCode(rffi.ULONGLONG,     'bigint_w.toulonglong', True),
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

    def getshape(self):
        return [self.array.len]

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


def make_array(mytype):
    W_ArrayBase = globals()['W_ArrayBase']

    unpack_driver = jit.JitDriver(name='unpack_array',
                                  greens=['tp'],
                                  reds=['self', 'w_iterator'])

    class W_Array(W_ArrayBase):
        itemsize = mytype.bytes
        typecode = mytype.typecode

        _attrs_ = ('space', 'len', 'allocated', '_lifeline_', 'buffer')

        def __init__(self, space):
            W_ArrayBase.__init__(self, space)
            self.buffer = lltype.nullptr(mytype.arraytype)

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
                    except OperationError as e:
                        if e.async(space):
                            raise
                        msg = "array item must be " + mytype.unwrap[:-2]
                        raise OperationError(space.w_TypeError, space.wrap(msg))
                else:
                    raise
            if mytype.convert:
                try:
                    item = getattr(item, mytype.convert)()
                except (ValueError, OverflowError):
                    raise oefmt(space.w_OverflowError,
                                "unsigned %d-byte integer out of range",
                                mytype.bytes)
                return rffi.cast(mytype.itemtype, item)
            if mytype.unwrap == 'str_w' or mytype.unwrap == 'unicode_w':
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
                                         self.space.wrap(msg))
            return result

        @rgc.must_be_light_finalizer
        def __del__(self):
            if self.buffer:
                lltype.free(self.buffer, flavor='raw')

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
                    if zero:
                        new_buffer = lltype.malloc(
                            mytype.arraytype, self.allocated, flavor='raw',
                            add_memory_pressure=True, zero=True)
                    else:
                        new_buffer = lltype.malloc(
                            mytype.arraytype, self.allocated, flavor='raw',
                            add_memory_pressure=True)
                        for i in range(min(size, self.len)):
                            new_buffer[i] = self.buffer[i]
                else:
                    self.len = size
                    return
            else:
                assert size == 0
                self.allocated = 0
                new_buffer = lltype.nullptr(mytype.arraytype)

            if self.buffer:
                lltype.free(self.buffer, flavor='raw')
            self.buffer = new_buffer
            self.len = size

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
                    buf = self.buffer
                    for num in lst:
                        buf[newlen] = self.item_from_int_or_float(num)
                        newlen += 1
                except OperationError:
                    self.setlen(newlen)
                    raise
                return

            # this is the common case: w_seq is a list or a tuple
            lst_w = space.listview_no_unpack(w_seq)
            if lst_w is not None:
                self.setlen(oldlen + len(lst_w))
                buf = self.buffer
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
                    if buf == self.buffer:
                        self.setlen(newlen)
                    raise
                return

            self._fromiterable(w_seq)

        def _fromiterable(self, w_seq):
            # a more careful case if w_seq happens to be a very large
            # iterable: don't copy the items into some intermediate list
            w_iterator = self.space.iter(w_seq)
            tp = self.space.type(w_iterator)
            while True:
                unpack_driver.jit_merge_point(tp=tp, self=self,
                                              w_iterator=w_iterator)
                space = self.space
                try:
                    w_item = space.next(w_iterator)
                except OperationError as e:
                    if not e.match(space, space.w_StopIteration):
                        raise
                    break  # done
                self.descr_append(space, w_item)

        def extend(self, w_iterable, accept_different_array=False):
            space = self.space
            if isinstance(w_iterable, W_Array):
                oldlen = self.len
                new = w_iterable.len
                self.setlen(self.len + new)
                i = 0
                while i < new:
                    if oldlen + i >= self.len:
                        self.setlen(oldlen + i + 1)
                    self.buffer[oldlen + i] = w_iterable.buffer[i]
                    i += 1
                self.setlen(oldlen + i)
            elif (not accept_different_array
                  and isinstance(w_iterable, W_ArrayBase)):
                raise oefmt(space.w_TypeError,
                            "can only extend with array of same kind")
            else:
                self.fromsequence(w_iterable)

        def _charbuf_start(self):
            return rffi.cast(rffi.CCHARP, self.buffer)

        def _buffer_as_unsigned(self):
            return rffi.cast(lltype.Unsigned, self.buffer)

        def _charbuf_stop(self):
            keepalive_until_here(self)

        def w_getitem(self, space, idx):
            item = self.buffer[idx]
            if mytype.typecode in 'bBhHil':
                item = rffi.cast(lltype.Signed, item)
            elif mytype.typecode == 'f':
                item = float(item)
            return space.wrap(item)

        # interface

        def descr_append(self, space, w_x):
            x = self.item_w(w_x)
            index = self.len
            self.setlen(index + 1)
            self.buffer[index] = x

        # List interface
        def descr_count(self, space, w_val):
            cnt = 0
            for i in range(self.len):
                # XXX jitdriver
                w_item = self.w_getitem(space, i)
                if space.is_true(space.eq(w_item, w_val)):
                    cnt += 1
            return space.wrap(cnt)

        def descr_index(self, space, w_val):
            for i in range(self.len):
                w_item = self.w_getitem(space, i)
                if space.is_true(space.eq(w_item, w_val)):
                    return space.wrap(i)
            raise oefmt(space.w_ValueError, "array.index(x): x not in list")

        def descr_reverse(self, space):
            b = self.buffer
            for i in range(self.len / 2):
                b[i], b[self.len - i - 1] = b[self.len - i - 1], b[i]

        def descr_pop(self, space, i):
            if i < 0:
                i += self.len
            if i < 0 or i >= self.len:
                raise oefmt(space.w_IndexError, "pop index out of range")
            w_val = self.w_getitem(space, i)
            while i < self.len - 1:
                self.buffer[i] = self.buffer[i + 1]
                i += 1
            self.setlen(self.len - 1)
            return w_val

        def descr_remove(self, space, w_val):
            w_idx = self.descr_index(space, w_val)
            self.descr_pop(space, space.int_w(w_idx))

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
            while i > idx:
                self.buffer[i] = self.buffer[i - 1]
                i -= 1
            self.buffer[i] = val

        def getitem_slice(self, space, w_idx):
            start, stop, step, size = space.decode_index4(w_idx, self.len)
            w_a = mytype.w_class(self.space)
            w_a.setlen(size, overallocate=False)
            assert step != 0
            j = 0
            for i in range(start, stop, step):
                w_a.buffer[j] = self.buffer[i]
                j += 1
            return w_a

        def setitem(self, space, w_idx, w_item):
            idx, stop, step = space.decode_index(w_idx, self.len)
            if step != 0:
                raise oefmt(self.space.w_TypeError,
                            "can only assign array to array slice")
            item = self.item_w(w_item)
            self.buffer[idx] = item

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
                for i in range(start, stop, step):
                    self.buffer[i] = w_item.buffer[j]
                    j += 1

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
            oldbuffer = self.buffer
            self.buffer = lltype.malloc(
                mytype.arraytype, max(self.len - (j - i), 0), flavor='raw',
                add_memory_pressure=True)
            if i:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, self.buffer),
                    rffi.cast(rffi.VOIDP, oldbuffer),
                    i * mytype.bytes
                )
            if j < self.len:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, rffi.ptradd(self.buffer, i)),
                    rffi.cast(rffi.VOIDP, rffi.ptradd(oldbuffer, j)),
                    (self.len - j) * mytype.bytes
                )
            self.len -= j - i
            self.allocated = self.len
            if oldbuffer:
                lltype.free(oldbuffer, flavor='raw')

        # Add and mul methods
        def descr_add(self, space, w_other):
            if not isinstance(w_other, W_Array):
                return space.w_NotImplemented
            a = mytype.w_class(space)
            a.setlen(self.len + w_other.len, overallocate=False)
            if self.len:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, a.buffer),
                    rffi.cast(rffi.VOIDP, self.buffer),
                    self.len * mytype.bytes
                )
            if w_other.len:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, rffi.ptradd(a.buffer, self.len)),
                    rffi.cast(rffi.VOIDP, w_other.buffer),
                    w_other.len * mytype.bytes
                )
            return a

        def descr_inplace_add(self, space, w_other):
            if not isinstance(w_other, W_Array):
                return space.w_NotImplemented
            oldlen = self.len
            otherlen = w_other.len
            self.setlen(oldlen + otherlen)
            if otherlen:
                rffi.c_memcpy(
                    rffi.cast(rffi.VOIDP, rffi.ptradd(self.buffer, oldlen)),
                    rffi.cast(rffi.VOIDP, w_other.buffer),
                    otherlen * mytype.bytes
                )
            return self

        def descr_mul(self, space, w_repeat):
            return _mul_helper(space, self, w_repeat, False)

        def descr_inplace_mul(self, space, w_repeat):
            return _mul_helper(space, self, w_repeat, True)

    def _mul_helper(space, self, w_repeat, is_inplace):
        try:
            repeat = space.getindex_w(w_repeat, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        repeat = max(repeat, 0)
        try:
            newlen = ovfcheck(self.len * repeat)
        except OverflowError:
            raise MemoryError
        oldlen = self.len
        if is_inplace:
            a = self
            start = 1
        else:
            a = mytype.w_class(space)
            start = 0
        # <a performance hack>
        if oldlen == 1:
            if mytype.unwrap == 'str_w' or mytype.unwrap == 'unicode_w':
                zero = not ord(self.buffer[0])
            elif mytype.unwrap == 'int_w' or mytype.unwrap == 'bigint_w':
                zero = not widen(self.buffer[0])
            #elif mytype.unwrap == 'float_w':
            #    value = ...float(self.buffer[0])  xxx handle the case of -0.0
            else:
                zero = False
            if zero:
                a.setlen(newlen, zero=True, overallocate=False)
                return a
            a.setlen(newlen, overallocate=False)
            item = self.buffer[0]
            for r in range(start, repeat):
                a.buffer[r] = item
            return a
        # </a performance hack>
        a.setlen(newlen, overallocate=False)
        for r in range(start, repeat):
            for i in range(oldlen):
                a.buffer[r * oldlen + i] = self.buffer[i]
        return a

    mytype.w_class = W_Array
    W_Array.constructor = W_Array
    name = 'ArrayType' + mytype.typecode
    W_Array.__name__ = 'W_' + name

for mytype in types.values():
    make_array(mytype)
del mytype

class State:
    def __init__(self, space):
        w_module = space.getbuiltinmodule('array')
        self.w_array_reconstructor = space.getattr(
            w_module, space.wrap("_array_reconstructor"))
