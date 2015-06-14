# TclObject, conversions with Python objects

from .tklib_cffi import ffi as tkffi, lib as tklib
import binascii

class TypeCache(object):
    def __init__(self):
        self.BooleanType = tklib.Tcl_GetObjType("boolean")
        self.ByteArrayType = tklib.Tcl_GetObjType("bytearray")
        self.DoubleType = tklib.Tcl_GetObjType("double")
        self.IntType = tklib.Tcl_GetObjType("int")
        self.BigNumType = None
        self.ListType = tklib.Tcl_GetObjType("list")
        self.ProcBodyType = tklib.Tcl_GetObjType("procbody")
        self.StringType = tklib.Tcl_GetObjType("string")

    def add_extra_types(self, app):
        # Some types are not registered in Tcl.
        result = app.call('expr', '2**63')
        typePtr = AsObj(result).typePtr
        if tkffi.string(typePtr.name) == "bignum":
            self.BigNumType = typePtr


def FromTclString(s):
    # If the result contains any bytes with the top bit set, it's
    # UTF-8 and we should decode it to Unicode.
    try:
        s.decode('ascii')
    except UnicodeDecodeError:
        try:
            return s.decode('utf8')
        except UnicodeDecodeError:
            # Tcl encodes null character as \xc0\x80
            try:
                return s.replace('\xc0\x80', '\x00').decode('utf-8')
            except UnicodeDecodeError:
                pass
    return s


# Only when tklib.HAVE_LIBTOMMATH!
def FromBignumObj(app, value):
    bigValue = tkffi.new("mp_int*")
    if tklib.Tcl_GetBignumFromObj(app.interp, value, bigValue) != tklib.TCL_OK:
        app.raiseTclError()
    try:
        numBytes = tklib.mp_unsigned_bin_size(bigValue)
        buf = tkffi.new("unsigned char[]", numBytes)
        bufSize_ptr = tkffi.new("unsigned long*", numBytes)
        if tklib.mp_to_unsigned_bin_n(
                bigValue, buf, bufSize_ptr) != tklib.MP_OKAY:
            raise MemoryError
        bytes = tkffi.buffer(buf)[0:bufSize_ptr[0]]
        sign = -1 if bigValue.sign == tklib.MP_NEG else 1
        return sign * int(binascii.hexlify(bytes), 16)
    finally:
        tklib.mp_clear(bigValue)

def FromObj(app, value):
    """Convert a TclObj pointer into a Python object."""
    typeCache = app._typeCache
    if not value.typePtr:
        buf = tkffi.buffer(value.bytes, value.length)
        return FromTclString(buf[:])

    if value.typePtr == typeCache.BooleanType:
        return bool(value.internalRep.longValue)
    if value.typePtr == typeCache.ByteArrayType:
        size = tkffi.new('int*')
        data = tklib.Tcl_GetByteArrayFromObj(value, size)
        return tkffi.buffer(data, size[0])[:]
    if value.typePtr == typeCache.DoubleType:
        return value.internalRep.doubleValue
    if value.typePtr == typeCache.IntType:
        return value.internalRep.longValue
    if value.typePtr == typeCache.BigNumType and tklib.HAVE_LIBTOMMATH:
        return FromBignumObj(app, value)
    if value.typePtr == typeCache.ListType:
        size = tkffi.new('int*')
        status = tklib.Tcl_ListObjLength(app.interp, value, size)
        if status == tklib.TCL_ERROR:
            app.raiseTclError()
        result = []
        tcl_elem = tkffi.new("Tcl_Obj**")
        for i in range(size[0]):
            status = tklib.Tcl_ListObjIndex(app.interp,
                                            value, i, tcl_elem)
            if status == tklib.TCL_ERROR:
                app.raiseTclError()
            result.append(FromObj(app, tcl_elem[0]))
        return tuple(result)
    if value.typePtr == typeCache.ProcBodyType:
        pass  # fall through and return tcl object.
    if value.typePtr == typeCache.StringType:
        buf = tklib.Tcl_GetUnicode(value)
        length = tklib.Tcl_GetCharLength(value)
        buf = tkffi.buffer(tkffi.cast("char*", buf), length*2)[:]
        return buf.decode('utf-16')

    return TclObject(value)

def AsObj(value):
    if isinstance(value, str):
        return tklib.Tcl_NewStringObj(value, len(value))
    elif isinstance(value, bool):
        return tklib.Tcl_NewBooleanObj(value)
    elif isinstance(value, int):
        return tklib.Tcl_NewLongObj(value)
    elif isinstance(value, float):
        return tklib.Tcl_NewDoubleObj(value)
    elif isinstance(value, tuple):
        argv = tkffi.new("Tcl_Obj*[]", len(value))
        for i in range(len(value)):
            argv[i] = AsObj(value[i])
        return tklib.Tcl_NewListObj(len(value), argv)
    elif isinstance(value, unicode):
        encoded = value.encode('utf-16')[2:]
        buf = tkffi.new("char[]", encoded)
        inbuf = tkffi.cast("Tcl_UniChar*", buf)
        return tklib.Tcl_NewUnicodeObj(buf, len(encoded)/2)
    elif isinstance(value, TclObject):
        tklib.Tcl_IncrRefCount(value._value)
        return value._value
    else:
        return AsObj(str(value))

class TclObject(object):
    def __new__(cls, value):
        self = object.__new__(cls)
        tklib.Tcl_IncrRefCount(value)
        self._value = value
        self._string = None
        return self

    def __del__(self):
        tklib.Tcl_DecrRefCount(self._value)

    def __str__(self):
        if self._string and isinstance(self._string, str):
            return self._string
        return tkffi.string(tklib.Tcl_GetString(self._value))

    def __repr__(self):
        return "<%s object at 0x%x>" % (
            self.typename, tkffi.cast("intptr_t", self._value))

    def __eq__(self, other):
        if not isinstance(other, TclObject):
            return NotImplemented
        return self._value == other._value

    @property
    def typename(self):
        return tkffi.string(self._value.typePtr.name)

    @property
    def string(self):
        if self._string is None:
            length = tkffi.new("int*")
            s = tklib.Tcl_GetStringFromObj(self._value, length)
            value = tkffi.buffer(s, length[0])[:]
            try:
                value.decode('ascii')
            except UnicodeDecodeError:
                value = value.decode('utf8')
            self._string = value
        return self._string
