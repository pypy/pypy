from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import rwinreg, rwin32

def raiseWindowsError(space, errcode, context):
    message = rwin32.FormatError(errcode)
    raise OperationError(space.w_WindowsError, space.wrap((errcode, message)))

class W_HKEY(Wrappable):
    def __init__(self, hkey):
        self.hkey = hkey

    def descr_nonzero(self, space):
        return self.wrap(self.hkey != 0)
    descr_nonzero.unwrap_spec = ['self', ObjSpace]

    def descr_repr(self, space):
        return space.wrap("<PyHKEY:0x%x>" % (self.hkey,))
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def descr_int(self, space):
        return space.wrap(self.hkey)
    descr_int.unwrap_spec = ['self', ObjSpace]

    def Close(self, space):
        CloseKey(space, self)
    Close.unwrap_spec = ['self', ObjSpace]

def new_HKEY(space, w_subtype, hkey):
    return space.wrap(W_HKEY(hkey))
descr_HKEY_new = interp2app(new_HKEY,
                            unwrap_spec=[ObjSpace, W_Root, int])

W_HKEY.typedef = TypeDef(
    "_winreg.HKEYType",
    __new__ = descr_HKEY_new,
    __repr__ = interp2app(W_HKEY.descr_repr),
    __int__ = interp2app(W_HKEY.descr_int),
    __nonzero__ = interp2app(W_HKEY.descr_nonzero),
    Close = interp2app(W_HKEY.Close),
    )

def hkey_w(w_hkey, space):
    if space.is_w(w_hkey, space.w_None):
        errstring = space.wrap("None is not a valid HKEY in this context")
        raise OperationError(space.w_TypeError, errstring)
    elif isinstance(w_hkey, W_HKEY):
        return w_hkey.hkey
    elif space.is_true(space.isinstance(w_hkey, space.w_int)):
        return space.int_w(w_hkey)
    elif space.is_true(space.isinstance(w_hkey, space.w_long)):
        return space.uint_w(w_hkey)
    else:
        errstring = space.wrap("The object is not a PyHKEY object")
        raise OperationError(space.w_TypeError, errstring)

def CloseKey(space, w_hkey):
    hkey = hkey_w(w_hkey, space)
    if hkey:
        ret = rwinreg.RegCloseKey(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegSetValue')
CloseKey.unwrap_spec = [ObjSpace, W_Root]

def SetValue(space, w_hkey, w_subkey, typ, value):
    if typ != rwinreg.REG_SZ:
        errstring = space.wrap("Type must be _winreg.REG_SZ")
        raise OperationError(space.w_ValueError, errstring)
    hkey = hkey_w(w_hkey, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.str_w(w_subkey)
    dataptr = rffi.str2charp(value)
    try:
        ret = rwinreg.RegSetValue(hkey, subkey, rwinreg.REG_SZ, dataptr, len(value))
    finally:
        rffi.free_charp(dataptr)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegSetValue')
SetValue.unwrap_spec = [ObjSpace, W_Root, W_Root, int, str]

def QueryValue(space, w_hkey, w_subkey):
    hkey = hkey_w(w_hkey, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.str_w(w_subkey)
    bufsize_p = lltype.malloc(rwin32.PLONG.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegQueryValue(hkey, subkey, None, bufsize_p)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegQueryValue')
        buf = lltype.malloc(rffi.CCHARP.TO, bufsize_p[0], flavor='raw')
        try:
            ret = rwinreg.RegQueryValue(hkey, subkey, buf, bufsize_p)
            if ret != 0:
                raiseWindowsError(space, ret, 'RegQueryValue')
            return space.wrap(rffi.charp2strn(buf, bufsize_p[0] - 1))
        finally:
            lltype.free(buf, flavor='raw')
    finally:
        lltype.free(bufsize_p, flavor='raw')
    if ret != 0:
        raiseWindowsError(space, ret, 'RegQueryValue')
QueryValue.unwrap_spec = [ObjSpace, W_Root, W_Root]

def convert_to_regdata(space, w_value, typ):
    buf = None

    if typ == rwinreg.REG_DWORD:
        if space.is_true(space.isinstance(w_value, space.w_int)):
            buflen = rffi.sizeof(rwin32.DWORD)
            buf = lltype.malloc(rffi.CArray(rwin32.DWORD), 1, flavor='raw')
            buf[0] = space.uint_w(w_value)

    elif typ == rwinreg.REG_SZ or typ == rwinreg.REG_EXPAND_SZ:
        if space.is_w(w_value, space.w_None):
            buflen = 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
            buf[0] = 0
        else:
            if space.is_true(space.isinstance(w_value, space.w_unicode)):
                w_value = space.call_method(w_value, 'encode',
                                            space.wrap('mbcs'))
            buf = rffi.str2charp(space.str_w(w_value))
            buflen = space.int_w(space.len(w_value)) + 1

    elif typ == rwinreg.REG_MULTI_SZ:
        if space.is_w(w_value, space.w_None):
            buflen = 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
            buf[0] = 0
        elif space.is_true(space.isinstance(w_value, space.w_list)):
            strings = []
            buflen = 0

            # unwrap strings and compute total size
            w_iter = space.iter(w_value)
            while True:
                try:
                    w_item = space.next(w_iter)
                    if space.is_true(space.isinstance(w_item, space.w_unicode)):
                        w_item = space.call_method(w_item, 'encode',
                                                   space.wrap('mbcs'))
                    item = space.str_w(w_item)
                    strings.append(item)
                    buflen += len(item) + 1
                except OperationError, e:
                    if not e.match(space, space.w_StopIteration):
                        raise       # re-raise other app-level exceptions
                    break
            buflen += 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')

            # Now copy data
            buflen = 0
            for string in strings:
                for i in range(len(string)):
                    buf[buflen + i] = string[i]
                buflen += len(string) + 1
                buf[buflen - 1] = '\0'
            buflen += 1
            buf[buflen - 1] = '\0'

    else: # REG_BINARY and ALL unknown data types.
        if space.is_w(w_value, space.w_None):
            buflen = 0
            buf = lltype.malloc(rffi.CCHARP.TO, 1, flavor='raw')
        else:
            value = space.bufferstr_w(w_value)
            buflen = len(value)
            buf = rffi.str2charp(value)

    if buf is not None:
        return rffi.cast(rffi.CCHARP, buf), buflen

    errstring = space.wrap("Could not convert the data to the specified type")
    raise OperationError(space.w_ValueError, errstring)

def convert_from_regdata(space, buf, buflen, typ):
    if typ == rwinreg.REG_DWORD:
        if not buflen:
            return 0
        return rffi.cast(rwin32.LPDWORD, buf)[0]

    elif typ == rwinreg.REG_SZ or typ == rwinreg.REG_EXPAND_SZ:
        if not buflen:
            return u""
        return rffi.charp2strn(rffi.cast(rffi.CCHARP, buf), buflen)

    elif typ == rwinreg.REG_MULTI_SZ:
        if not buflen:
            return []
        i = 0
        l = []
        while i < buflen and buf[i]:
            s = []
            while i < buflen and buf[i] != '\0':
                s.append(buf[i])
                i += 1
            if len(s) == 0:
                break
            l.append(''.join(s))
            i += 1
        return l

    else: # REG_BINARY and all other types
        return rffi.charpsize2str(buf, buflen)

def SetValueEx(space, w_hkey, value_name, w_reserved, typ, w_value):
    hkey = hkey_w(w_hkey, space)
    buf, buflen = convert_to_regdata(space, w_value, typ)
    try:
        ret = rwinreg.RegSetValueEx(hkey, value_name, 0, typ, buf, buflen)
    finally:
        lltype.free(buf, flavor='raw')
    if ret != 0:
        raiseWindowsError(space, ret, 'RegSetValueEx')
SetValueEx.unwrap_spec = [ObjSpace, W_Root, str, W_Root, int, W_Root]

def QueryValueEx(space, w_hkey, subkey):
    hkey = hkey_w(w_hkey, space)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)
    retDataSize = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegQueryValueEx(hkey, subkey, null_dword, null_dword,
                                      None, retDataSize)
        if ret != 0:
            print "AFA??", hkey, subkey
            raiseWindowsError(space, ret, 'RegQueryValueEx')
        databuf = lltype.malloc(rffi.CCHARP.TO, retDataSize[0], flavor='raw')
        try:
            retType = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
            try:

                ret = rwinreg.RegQueryValueEx(hkey, subkey, null_dword,
                                              retType, databuf, retDataSize)
                if ret != 0:
                    raiseWindowsError(space, ret, 'RegQueryValueEx')
                return space.wrap((
                    convert_from_regdata(space, databuf,
                                         retDataSize[0], retType[0]),
                    retType[0],
                    ))
            finally:
                lltype.free(retType, flavor='raw')
        finally:
            lltype.free(databuf, flavor='raw')
    finally:
        lltype.free(retDataSize, flavor='raw')

QueryValueEx.unwrap_spec = [ObjSpace, W_Root, str]

def CreateKey(space, w_hkey, subkey):
    hkey = hkey_w(w_hkey, space)
    rethkey = lltype.malloc(rwinreg.PHKEY.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegCreateKey(hkey, subkey, rethkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'CreateKey')
        return space.wrap(W_HKEY(rethkey[0]))
    finally:
        lltype.free(rethkey, flavor='raw')
CreateKey.unwrap_spec = [ObjSpace, W_Root, str]

def OpenKey(space, w_hkey, subkey, res=0, sam=rwinreg.KEY_READ):
    hkey = hkey_w(w_hkey, space)
    rethkey = lltype.malloc(rwinreg.PHKEY.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegOpenKeyEx(hkey, subkey, res, sam, rethkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegOpenKeyEx')
        return space.wrap(W_HKEY(rethkey[0]))
    finally:
        lltype.free(rethkey, flavor='raw')
OpenKey.unwrap_spec = [ObjSpace, W_Root, str, int, rffi.r_uint]

def EnumValue(space, w_hkey, index):
    hkey = hkey_w(w_hkey, space)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)

    retValueSize = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
    try:
        retDataSize = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
        try:
            ret = rwinreg.RegQueryInfoKey(
                hkey, None, null_dword, null_dword,
                null_dword, null_dword, null_dword,
                null_dword, retValueSize, retDataSize,
                null_dword, lltype.nullptr(rwin32.PFILETIME.TO))
            if ret != 0:
                raiseWindowsError(space, ret, 'RegQueryInfoKey')
            # include null terminators
            retValueSize[0] += 1
            retDataSize[0] += 1

            valuebuf = lltype.malloc(rffi.CCHARP.TO, retValueSize[0],
                                     flavor='raw')
            try:
                databuf = lltype.malloc(rffi.CCHARP.TO, retDataSize[0],
                                        flavor='raw')
                try:
                    retType = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
                    try:
                        ret = rwinreg.RegEnumValue(
                            hkey, index, valuebuf, retValueSize,
                            null_dword, retType, databuf, retDataSize)
                        if ret != 0:
                            raiseWindowsError(space, ret, 'RegEnumValue')

                        return space.wrap((
                            rffi.charp2str(valuebuf),
                            convert_from_regdata(space, databuf,
                                                 retDataSize[0], retType[0]),
                            retType[0],
                            ))
                    finally:
                        lltype.free(retType, flavor='raw')
                finally:
                    lltype.free(databuf, flavor='raw')
            finally:
                lltype.free(valuebuf, flavor='raw')
        finally:
            lltype.free(retDataSize, flavor='raw')
    finally:
        lltype.free(retValueSize, flavor='raw')

EnumValue.unwrap_spec = [ObjSpace, W_Root, int]

def QueryInfoKey(space, w_hkey):
    hkey = hkey_w(w_hkey, space)
    nSubKeys = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
    try:
        nValues = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
        try:
            ft = lltype.malloc(rwin32.PFILETIME.TO, 1, flavor='raw')
            try:
                null_dword = lltype.nullptr(rwin32.LPDWORD.TO)
                ret = rwinreg.RegQueryInfoKey(
                    hkey, None, null_dword, null_dword,
                    nSubKeys, null_dword, null_dword,
                    nValues, null_dword, null_dword,
                    null_dword, ft)
                if ret != 0:
                    raiseWindowsError(space, ret, 'RegQueryInfoKey')
                l = (ft[0].c_dwLowDateTime +
                     (ft[0].c_dwHighDateTime << 32))
                return space.wrap((nSubKeys[0], nValues[0], l))
            finally:
                lltype.free(ft, flavor='raw')
        finally:
            lltype.free(nValues, flavor='raw')
    finally:
        lltype.free(nSubKeys, flavor='raw')
QueryInfoKey.unwrap_spec = [ObjSpace, W_Root]
