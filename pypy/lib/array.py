"""This module defines an object type which can efficiently represent
an array of basic values: characters, integers, floating point
numbers.  Arrays are sequence types and behave very much like lists,
except that the type of objects stored in them is constrained.  The
type is specified at object creation time by using a type code, which
is a single character.  The following type codes are defined:

    Type code   C Type             Minimum size in bytes 
    'c'         character          1 
    'b'         signed integer     1 
    'B'         unsigned integer   1 
    'u'         Unicode character  2 
    'h'         signed integer     2 
    'H'         unsigned integer   2 
    'i'         signed integer     2 
    'I'         unsigned integer   2 
    'l'         signed integer     4 
    'L'         unsigned integer   4 
    'f'         floating point     4 
    'd'         floating point     8 

The constructor is:

array(typecode [, initializer]) -- create a new array
"""

from struct import calcsize, pack, pack_into, unpack_from
import operator

# the buffer-like object to use internally: trying from
# various places in order...
try:
    import _rawffi                    # a reasonable implementation based
    _RAWARRAY = _rawffi.Array('c')    # on raw_malloc, and providing a
    def bytebuffer(size):             # real address
        return _RAWARRAY(size, autofree=True)
    def getbufaddress(buf):
        return buf.buffer
except ImportError:
    try:
        from __pypy__ import bytebuffer     # a reasonable implementation
        def getbufaddress(buf):             # compatible with oo backends,
            return 0                        # but no address
    except ImportError:
        # not running on PyPy.  Fall back to ctypes...
        import ctypes
        bytebuffer = ctypes.create_string_buffer
        def getbufaddress(buf):
            voidp = ctypes.cast(ctypes.pointer(buf), ctypes.c_void_p)
            return voidp.value

# ____________________________________________________________

TYPECODES = "cbBuhHiIlLfd"

class array(object):
    """array(typecode [, initializer]) -> array
    
    Return a new array whose items are restricted by typecode, and
    initialized from the optional initializer value, which must be a list,
    string. or iterable over elements of the appropriate type.
    
    Arrays represent basic values and behave very much like lists, except
    the type of objects stored in them is constrained.
    
    Methods:
    
    append() -- append a new item to the end of the array
    buffer_info() -- return information giving the current memory info
    byteswap() -- byteswap all the items of the array
    count() -- return number of occurences of an object
    extend() -- extend array by appending multiple elements from an iterable
    fromfile() -- read items from a file object
    fromlist() -- append items from the list
    fromstring() -- append items from the string
    index() -- return index of first occurence of an object
    insert() -- insert a new item into the array at a provided position
    pop() -- remove and return item (default last)
    read() -- DEPRECATED, use fromfile()
    remove() -- remove first occurence of an object
    reverse() -- reverse the order of the items in the array
    tofile() -- write all items to a file object
    tolist() -- return the array converted to an ordinary list
    tostring() -- return the array converted to a string
    write() -- DEPRECATED, use tofile()
    
    Attributes:
    
    typecode -- the typecode character used to create the array
    itemsize -- the length in bytes of one array item
    """
    __slots__ = ["typecode", "itemsize", "_data", "_descriptor", "__weakref__"]

    def __new__(cls, typecode, initializer=[]):
        self = object.__new__(cls)
        if not isinstance(typecode, str) or len(typecode) != 1:
            raise TypeError(
                     "array() argument 1 must be char, not %s" % type(typecode))
        if typecode not in TYPECODES:
            raise ValueError(
                  "bad typecode (must be one of %s)" % ', '.join(TYPECODES))
        self._data = bytebuffer(0)
        self.typecode = typecode
        self.itemsize = calcsize(typecode)
        if isinstance(initializer, list):
            self.fromlist(initializer)
        elif isinstance(initializer, str):
            self.fromstring(initializer)
        elif isinstance(initializer, unicode) and self.typecode == "u":
            self.fromunicode(initializer)
        else:
            self.extend(initializer)
        return self

    def _clear(self):
        self._data = bytebuffer(0)

    ##### array-specific operations

    def fromfile(self, f, n):
        """Read n objects from the file object f and append them to the end of
        the array. Also called as read."""
        if not isinstance(f, file):
            raise TypeError("arg1 must be open file")
        size = self.itemsize * n
        item = f.read(size)
        if len(item) < size:
            raise EOFError("not enough items in file")
        self.fromstring(item)

    def fromlist(self, l):
        """Append items to array from list."""
        if not isinstance(l, list):
            raise TypeError("arg must be list")
        self._fromiterable(l)
        
    def fromstring(self, s):
        """Appends items from the string, interpreting it as an array of machine
        values, as if it had been read from a file using the fromfile()
        method."""
        if isinstance(s, unicode):
            s = str(s)
        self._frombuffer(s)

    def _frombuffer(self, s):
        length = len(s)
        if length % self.itemsize != 0:
            raise ValueError("string length not a multiple of item size")
        boundary = len(self._data)
        newdata = bytebuffer(boundary + length)
        newdata[:boundary] = self._data
        newdata[boundary:] = s
        self._data = newdata

    def fromunicode(self, ustr):
        """Extends this array with data from the unicode string ustr. The array
        must be a type 'u' array; otherwise a ValueError is raised. Use
        array.fromstring(ustr.encode(...)) to append Unicode data to an array of
        some other type."""
        if not self.typecode == "u":
            raise ValueError(
                          "fromunicode() may only be called on type 'u' arrays")
        # XXX the following probable bug is not emulated:
        # CPython accepts a non-unicode string or a buffer, and then
        # behaves just like fromstring(), except that it strangely truncates
        # string arguments at multiples of the unicode byte size.
        # Let's only accept unicode arguments for now.
        if not isinstance(ustr, unicode):
            raise TypeError("fromunicode() argument should probably be "
                            "a unicode string")
        # _frombuffer() does the currect thing using
        # the buffer behavior of unicode objects
        self._frombuffer(buffer(ustr))

    def tofile(self, f):
        """Write all items (as machine values) to the file object f.  Also
        called as write."""
        if not isinstance(f, file):
            raise TypeError("arg must be open file")
        f.write(self.tostring())
        
    def tolist(self):
        """Convert array to an ordinary list with the same items."""
        count = len(self._data) // self.itemsize
        return list(unpack_from('%d%s' % (count, self.typecode), self._data))

    def tostring(self):
        return self._data[:]

    def __buffer__(self):
        return buffer(self._data)

    def tounicode(self):
        """Convert the array to a unicode string. The array must be a type 'u'
        array; otherwise a ValueError is raised. Use array.tostring().decode()
        to obtain a unicode string from an array of some other type."""
        if self.typecode != "u":
            raise ValueError("tounicode() may only be called on type 'u' arrays")
        # XXX performance is not too good
        return u"".join(self.tolist())

    def byteswap(self):
        """Byteswap all items of the array.  If the items in the array are not
        1, 2, 4, or 8 bytes in size, RuntimeError is raised."""
        if self.itemsize not in [1, 2, 4, 8]:
            raise RuntimeError("byteswap not supported for this array")
        # XXX slowish
        itemsize = self.itemsize
        bytes = self._data
        for start in range(0, len(bytes), itemsize):
            stop = start + itemsize
            bytes[start:stop] = bytes[start:stop][::-1]

    def buffer_info(self):
        """Return a tuple (address, length) giving the current memory address
        and the length in items of the buffer used to hold array's contents. The
        length should be multiplied by the itemsize attribute to calculate the
        buffer length in bytes. On PyPy the address might be meaningless
        (returned as 0), depending on the available modules."""
        return (getbufaddress(self._data), len(self))
    
    read = fromfile

    write = tofile

    ##### general object protocol
    
    def __repr__(self):
        if len(self._data) == 0:
            return "array('%s')" % self.typecode
        elif self.typecode == "c":
            return "array('%s', %s)" % (self.typecode, repr(self.tostring()))
        elif self.typecode == "u":
            return "array('%s', %s)" % (self.typecode, repr(self.tounicode()))
        else:
            return "array('%s', %s)" % (self.typecode, repr(self.tolist()))

    def __copy__(self):
        a = array(self.typecode)
        a._data = bytebuffer(len(self._data))
        a._data[:] = self._data
        return a

    def __eq__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self._data) == buffer(other._data)
        else:
            return self.tolist() == other.tolist()

    def __ne__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self._data) != buffer(other._data)
        else:
            return self.tolist() != other.tolist()

    def __lt__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self._data) < buffer(other._data)
        else:
            return self.tolist() < other.tolist()

    def __gt__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self._data) > buffer(other._data)
        else:
            return self.tolist() > other.tolist()

    def __le__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self._data) <= buffer(other._data)
        else:
            return self.tolist() <= other.tolist()

    def __ge__(self, other):
        if not isinstance(other, array):
            return NotImplemented
        if self.typecode == 'c':
            return buffer(self._data) >= buffer(other._data)
        else:
            return self.tolist() >= other.tolist()

    ##### list methods
    
    def append(self, x):
        """Append new value x to the end of the array."""
        self._frombuffer(pack(self.typecode, x))

    def count(self, x):
        """Return number of occurences of x in the array."""
        return operator.countOf(self, x)

    def extend(self, iterable):
        """Append items to the end of the array."""
        if isinstance(iterable, array) \
                                    and not self.typecode == iterable.typecode:
            raise TypeError("can only extend with array of same kind")
        self._fromiterable(iterable)

    def index(self, x):
        """Return index of first occurence of x in the array."""
        return operator.indexOf(self, x)
    
    def insert(self, i, x):
        """Insert a new item x into the array before position i."""
        seqlength = len(self)
        if i < 0:
            i += seqlength
            if i < 0:
                i = 0
        elif i > seqlength:
            i = seqlength
        boundary = i * self.itemsize
        data = pack(self.typecode, x)
        newdata = bytebuffer(len(self._data) + len(data))
        newdata[:boundary] = self._data[:boundary]
        newdata[boundary:boundary+self.itemsize] = data
        newdata[boundary+self.itemsize:] = self._data[boundary:]
        self._data = newdata
        
    def pop(self, i=-1):
        """Return the i-th element and delete it from the array. i defaults to
        -1."""
        seqlength = len(self)
        if i < 0:
            i += seqlength
        if not (0 <= i < seqlength):
            raise IndexError(i)
        boundary = i * self.itemsize
        result = unpack_from(self.typecode, self._data, boundary)[0]
        newdata = bytebuffer(len(self._data) - self.itemsize)
        newdata[:boundary] = self._data[:boundary]
        newdata[boundary:] = self._data[boundary+self.itemsize:]
        self._data = newdata
        return result
        
    def remove(self, x):
        """Remove the first occurence of x in the array."""
        self.pop(self.index(x))
        
    def reverse(self):
        """Reverse the order of the items in the array."""
        lst = self.tolist()
        lst.reverse()
        self._clear()
        self.fromlist(lst)

    ##### list protocol
    
    def __len__(self):
        return len(self._data) // self.itemsize
    
    def __add__(self, other):
        if not isinstance(other, array):
            raise TypeError("can only append array to array")
        if self.typecode != other.typecode:
            raise TypeError("bad argument type for built-in operation")
        return array(self.typecode, buffer(self._data) + buffer(other._data))

    def __mul__(self, repeat):
        return array(self.typecode, buffer(self._data) * repeat)

    __rmul__ = __mul__

    def __getitem__(self, i):
        seqlength = len(self)
        if isinstance(i, slice):
            start, stop, step = i.indices(seqlength)
            if step != 1:
                sublist = self.tolist()[i]    # fall-back
                return array(self.typecode, sublist)
            if start < 0:
                start = 0
            if stop < start:
                stop = start
            assert stop <= seqlength
            return array(self.typecode, self._data[start * self.itemsize :
                                                   stop * self.itemsize])
        else:
            if i < 0:
                i += seqlength
            if self.typecode == 'c':  # speed trick
                return self._data[i]
            if not (0 <= i < seqlength):
                raise IndexError(i)
            boundary = i * self.itemsize
            return unpack_from(self.typecode, self._data, boundary)[0]

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def __setitem__(self, i, x):
        if isinstance(i, slice):
            if (not isinstance(x, array)
                or self.typecode != x.typecode):
                raise TypeError("can only assign array of same kind"
                                " to array slice")
            seqlength = len(self)
            start, stop, step = i.indices(seqlength)
            if step != 1:
                sublist = self.tolist()    # fall-back
                sublist[i] = x.tolist()
                self._clear()
                self.fromlist(sublist)
                return
            if start < 0:
                start = 0
            if stop < start:
                stop = start
            assert stop <= seqlength
            boundary1 = start * self.itemsize
            boundary2 = stop * self.itemsize
            boundary2new = boundary1 + len(x._data)
            if boundary2 == boundary2new:
                self._data[boundary1:boundary2] = x._data
            else:
                newdata = bytebuffer(len(self._data) + boundary2new-boundary2)
                newdata[:boundary1] = self._data[:boundary1]
                newdata[boundary1:boundary2new] = x._data
                newdata[boundary2new:] = self._data[boundary2:]
                self._data = newdata
        else:
            seqlength = len(self)
            if i < 0:
                i += seqlength
            if self.typecode == 'c':  # speed trick
                self._data[i] = x
                return
            if not (0 <= i < seqlength):
                raise IndexError(i)
            boundary = i * self.itemsize
            pack_into(self.typecode, self._data, boundary, x)

    def __setslice__(self, i, j, x):
        self.__setitem__(slice(i, j), x)

    def __delitem__(self, i):
        if isinstance(i, slice):
            seqlength = len(self)
            start, stop, step = i.indices(seqlength)
            if start < 0:
                start = 0
            if stop < start:
                stop = start
            assert stop <= seqlength
            if step != 1:
                sublist = self.tolist()    # fall-back
                del sublist[i]
                self._clear()
                self.fromlist(sublist)
                return
            dellength = stop - start
            boundary1 = start * self.itemsize
            boundary2 = stop * self.itemsize
            newdata = bytebuffer(len(self._data) - (boundary2-boundary1))
            newdata[:boundary1] = self._data[:boundary1]
            newdata[boundary1:] = self._data[boundary2:]
            self._data = newdata
        else:            
            seqlength = len(self)
            if i < 0:
                i += seqlength
            if not (0 <= i < seqlength):
                raise IndexError(i)
            boundary = i * self.itemsize
            newdata = bytebuffer(len(self._data) - self.itemsize)
            newdata[:boundary] = self._data[:boundary]
            newdata[boundary:] = self._data[boundary+self.itemsize:]
            self._data = newdata

    def __delslice__(self, i, j):
        self.__delitem__(slice(i, j))

    def __contains__(self, item):
        for x in self:
            if x == item:
                return True
        return False

    def __iadd__(self, other):
        if not isinstance(other, array):
            raise TypeError("can only extend array with array")
        self.extend(other)
        return self

    def __imul__(self, repeat):
        newdata = buffer(self._data) * repeat
        self._data = bytebuffer(len(newdata))
        self._data[:] = newdata
        return self

    def __iter__(self):
        p = 0
        typecode = self.typecode
        itemsize = self.itemsize
        while p < len(self._data):
            yield unpack_from(typecode, self._data, p)[0]
            p += itemsize

    ##### internal methods

    def _fromiterable(self, iterable):
        iterable = tuple(iterable)
        n = len(iterable)
        boundary = len(self._data)
        newdata = bytebuffer(boundary + n * self.itemsize)
        newdata[:boundary] = self._data
        pack_into('%d%s' % (n, self.typecode), newdata, boundary, *iterable)
        self._data = newdata

ArrayType = array
