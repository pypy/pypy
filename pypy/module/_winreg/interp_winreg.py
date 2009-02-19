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
SetValue.unwrap_spec = [ObjSpace, W_Root, W_Root, int, str]

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
