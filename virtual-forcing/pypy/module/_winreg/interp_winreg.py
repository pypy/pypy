from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import rwinreg, rwin32

def raiseWindowsError(space, errcode, context):
    message = rwin32.FormatError(errcode)
    raise OperationError(space.w_WindowsError,
                         space.newtuple([space.wrap(errcode),
                                         space.wrap(message)]))

class W_HKEY(Wrappable):
    def __init__(self, hkey):
        self.hkey = hkey

    def descr_del(self, space):
        self.Close(space)
    descr_del.unwrap_spec = ['self', ObjSpace]

    def descr_nonzero(self, space):
        return space.wrap(self.hkey != 0)
    descr_nonzero.unwrap_spec = ['self', ObjSpace]

    def descr_repr(self, space):
        return space.wrap("<PyHKEY:0x%x>" % (self.hkey,))
    descr_repr.unwrap_spec = ['self', ObjSpace]

    def descr_int(self, space):
        return space.wrap(self.hkey)
    descr_int.unwrap_spec = ['self', ObjSpace]

    def Close(self, space):
        """key.Close() - Closes the underlying Windows handle.
If the handle is already closed, no error is raised."""
        CloseKey(space, self)
    Close.unwrap_spec = ['self', ObjSpace]

    def Detach(self, space):
        """int = key.Detach() - Detaches the Windows handle from the handle object.

The result is the value of the handle before it is detached.  If the
handle is already detached, this will return zero.

After calling this function, the handle is effectively invalidated,
but the handle is not closed.  You would call this function when you
need the underlying win32 handle to exist beyond the lifetime of the
handle object.
On 64 bit windows, the result of this function is a long integer"""
        hkey = self.hkey
        self.hkey = 0
        return space.wrap(hkey)
    Detach.unwrap_spec = ['self', ObjSpace]

def new_HKEY(space, w_subtype, hkey):
    return space.wrap(W_HKEY(hkey))
descr_HKEY_new = interp2app(new_HKEY,
                            unwrap_spec=[ObjSpace, W_Root, int])

W_HKEY.typedef = TypeDef(
    "_winreg.HKEYType",
    __doc__ = """\
PyHKEY Object - A Python object, representing a win32 registry key.

This object wraps a Windows HKEY object, automatically closing it when
the object is destroyed.  To guarantee cleanup, you can call either
the Close() method on the PyHKEY, or the CloseKey() method.

All functions which accept a handle object also accept an integer - 
however, use of the handle object is encouraged.

Functions:
Close() - Closes the underlying handle.
Detach() - Returns the integer Win32 handle, detaching it from the object

Properties:
handle - The integer Win32 handle.

Operations:
__nonzero__ - Handles with an open object return true, otherwise false.
__int__ - Converting a handle to an integer returns the Win32 handle.
__cmp__ - Handle objects are compared using the handle value.""",
    __new__ = descr_HKEY_new,
    __del__ = interp2app(W_HKEY.descr_del),
    __repr__ = interp2app(W_HKEY.descr_repr),
    __int__ = interp2app(W_HKEY.descr_int),
    __nonzero__ = interp2app(W_HKEY.descr_nonzero),
    Close = interp2app(W_HKEY.Close),
    Detach = interp2app(W_HKEY.Detach),
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
    """CloseKey(hkey) - Closes a previously opened registry key.

The hkey argument specifies a previously opened key.

Note that if the key is not closed using this method, it will be
closed when the hkey object is destroyed by Python."""
    hkey = hkey_w(w_hkey, space)
    if hkey:
        ret = rwinreg.RegCloseKey(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegCloseKey')
CloseKey.unwrap_spec = [ObjSpace, W_Root]

def FlushKey(space, w_hkey):
    """FlushKey(key) - Writes all the attributes of a key to the registry.

key is an already open key, or any one of the predefined HKEY_* constants.

It is not necessary to call RegFlushKey to change a key.
Registry changes are flushed to disk by the registry using its lazy flusher.
Registry changes are also flushed to disk at system shutdown.
Unlike CloseKey(), the FlushKey() method returns only when all the data has
been written to the registry.
An application should only call FlushKey() if it requires absolute certainty that registry changes are on disk.
If you don't know whether a FlushKey() call is required, it probably isn't."""
    hkey = hkey_w(w_hkey, space)
    if hkey:
        ret = rwinreg.RegFlushKey(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegFlushKey')
FlushKey.unwrap_spec = [ObjSpace, W_Root]

def LoadKey(space, w_hkey, subkey, filename):
    """LoadKey(key, sub_key, file_name) - Creates a subkey under the specified key
and stores registration information from a specified file into that subkey.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that identifies the sub_key to load
file_name is the name of the file to load registry data from.
 This file must have been created with the SaveKey() function.
 Under the file allocation table (FAT) file system, the filename may not
have an extension.

A call to LoadKey() fails if the calling process does not have the
SE_RESTORE_PRIVILEGE privilege.

If key is a handle returned by ConnectRegistry(), then the path specified
in fileName is relative to the remote computer.

The docs imply key must be in the HKEY_USER or HKEY_LOCAL_MACHINE tree"""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegLoadKey(hkey, subkey, filename)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegLoadKey')
LoadKey.unwrap_spec = [ObjSpace, W_Root, str, str]

def SaveKey(space, w_hkey, filename):
    """SaveKey(key, file_name) - Saves the specified key, and all its subkeys to the specified file.

key is an already open key, or any one of the predefined HKEY_* constants.
file_name is the name of the file to save registry data to.
 This file cannot already exist. If this filename includes an extension,
 it cannot be used on file allocation table (FAT) file systems by the
 LoadKey(), ReplaceKey() or RestoreKey() methods.

If key represents a key on a remote computer, the path described by
file_name is relative to the remote computer.
The caller of this method must possess the SeBackupPrivilege security privilege.
This function passes NULL for security_attributes to the API."""
    hkey = hkey_w(w_hkey, space)
    pSA = 0
    ret = rwinreg.RegSaveKey(hkey, filename, None)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegSaveKey')
SaveKey.unwrap_spec = [ObjSpace, W_Root, str]

def SetValue(space, w_hkey, w_subkey, typ, value):
    """SetValue(key, sub_key, type, value) - Associates a value with a specified key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that names the subkey with which the value is associated.
type is an integer that specifies the type of the data.  Currently this
 must be REG_SZ, meaning only strings are supported.
value is a string that specifies the new value.

If the key specified by the sub_key parameter does not exist, the SetValue
function creates it.

Value lengths are limited by available memory. Long values (more than
2048 bytes) should be stored as files with the filenames stored in
the configuration registry.  This helps the registry perform efficiently.

The key identified by the key parameter must have been opened with
KEY_SET_VALUE access."""
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
    """string = QueryValue(key, sub_key) - retrieves the unnamed value for a key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that holds the name of the subkey with which the value
 is associated.  If this parameter is None or empty, the function retrieves
 the value set by the SetValue() method for the key identified by key.

Values in the registry have name, type, and data components. This method
retrieves the data for a key's first value that has a NULL name.
But the underlying API call doesn't return the type, Lame Lame Lame, DONT USE THIS!!!"""
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
            buf1 = lltype.malloc(rffi.CArray(rwin32.DWORD), 1, flavor='raw')
            buf1[0] = space.uint_w(w_value)
            buf = rffi.cast(rffi.CCHARP, buf1)

    elif typ == rwinreg.REG_SZ or typ == rwinreg.REG_EXPAND_SZ:
        if space.is_w(w_value, space.w_None):
            buflen = 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
            buf[0] = '\0'
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
            buf[0] = '\0'
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
            buf[0] = '\0'
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
            return space.wrap(0)
        d = rffi.cast(rwin32.LPDWORD, buf)[0]
        return space.wrap(d)

    elif typ == rwinreg.REG_SZ or typ == rwinreg.REG_EXPAND_SZ:
        if not buflen:
            return space.wrap("")
        s = rffi.charp2strn(rffi.cast(rffi.CCHARP, buf), buflen)
        return space.wrap(s)

    elif typ == rwinreg.REG_MULTI_SZ:
        if not buflen:
            return space.newlist([])
        i = 0
        l = []
        while i < buflen and buf[i]:
            s = []
            while i < buflen and buf[i] != '\0':
                s.append(buf[i])
                i += 1
            if len(s) == 0:
                break
            s = ''.join(s)
            l.append(space.wrap(s))
            i += 1
        return space.newlist(l)

    else: # REG_BINARY and all other types
        return space.wrap(rffi.charpsize2str(buf, buflen))

def SetValueEx(space, w_hkey, value_name, w_reserved, typ, w_value):
    """SetValueEx(key, value_name, reserved, type, value) - Stores data in the value field of an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value_name is a string containing the name of the value to set, or None
type is an integer that specifies the type of the data.  This should be one of:
  REG_BINARY -- Binary data in any form.
  REG_DWORD -- A 32-bit number.
  REG_DWORD_LITTLE_ENDIAN -- A 32-bit number in little-endian format.
  REG_DWORD_BIG_ENDIAN -- A 32-bit number in big-endian format.
  REG_EXPAND_SZ -- A null-terminated string that contains unexpanded references
                   to environment variables (for example, %PATH%).
  REG_LINK -- A Unicode symbolic link.
  REG_MULTI_SZ -- An sequence of null-terminated strings, terminated by
                  two null characters.  Note that Python handles this
                  termination automatically.
  REG_NONE -- No defined value type.
  REG_RESOURCE_LIST -- A device-driver resource list.
  REG_SZ -- A null-terminated string.
reserved can be anything - zero is always passed to the API.
value is a string that specifies the new value.

This method can also set additional value and type information for the
specified key.  The key identified by the key parameter must have been
opened with KEY_SET_VALUE access.

To open the key, use the CreateKeyEx() or OpenKeyEx() methods.

Value lengths are limited by available memory. Long values (more than
2048 bytes) should be stored as files with the filenames stored in
the configuration registry.  This helps the registry perform efficiently."""
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
    """value,type_id = QueryValueEx(key, value_name) - Retrieves the type and data for a specified value name associated with an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value_name is a string indicating the value to query"""
    hkey = hkey_w(w_hkey, space)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)
    retDataSize = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegQueryValueEx(hkey, subkey, null_dword, null_dword,
                                      None, retDataSize)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegQueryValueEx')
        databuf = lltype.malloc(rffi.CCHARP.TO, retDataSize[0], flavor='raw')
        try:
            retType = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
            try:

                ret = rwinreg.RegQueryValueEx(hkey, subkey, null_dword,
                                              retType, databuf, retDataSize)
                if ret != 0:
                    raiseWindowsError(space, ret, 'RegQueryValueEx')
                return space.newtuple([
                    convert_from_regdata(space, databuf,
                                         retDataSize[0], retType[0]),
                    space.wrap(retType[0]),
                    ])
            finally:
                lltype.free(retType, flavor='raw')
        finally:
            lltype.free(databuf, flavor='raw')
    finally:
        lltype.free(retDataSize, flavor='raw')

QueryValueEx.unwrap_spec = [ObjSpace, W_Root, str]

def CreateKey(space, w_hkey, subkey):
    """key = CreateKey(key, sub_key) - Creates or opens the specified key.

key is an already open key, or one of the predefined HKEY_* constants
sub_key is a string that names the key this method opens or creates.
 If key is one of the predefined keys, sub_key may be None. In that case,
 the handle returned is the same key handle passed in to the function.

If the key already exists, this function opens the existing key

The return value is the handle of the opened key.
If the function fails, an exception is raised."""
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

def DeleteKey(space, w_hkey, subkey):
    """DeleteKey(key, sub_key) - Deletes the specified key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that must be a subkey of the key identified by the key parameter.
 This value must not be None, and the key may not have subkeys.

This method can not delete keys with subkeys.

If the method succeeds, the entire key, including all of its values,
is removed.  If the method fails, an EnvironmentError exception is raised."""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegDeleteKey(hkey, subkey)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegDeleteKey')
DeleteKey.unwrap_spec = [ObjSpace, W_Root, str]

def DeleteValue(space, w_hkey, subkey):
    """DeleteValue(key, value) - Removes a named value from a registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value is a string that identifies the value to remove."""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegDeleteValue(hkey, subkey)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegDeleteValue')
DeleteValue.unwrap_spec = [ObjSpace, W_Root, str]

def OpenKey(space, w_hkey, subkey, res=0, sam=rwinreg.KEY_READ):
    """key = OpenKey(key, sub_key, res = 0, sam = KEY_READ) - Opens the specified key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that identifies the sub_key to open
res is a reserved integer, and must be zero.  Default is zero.
sam is an integer that specifies an access mask that describes the desired
 security access for the key.  Default is KEY_READ

The result is a new handle to the specified key
If the function fails, an EnvironmentError exception is raised."""
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
    """tuple = EnumValue(key, index) - Enumerates values of an open registry key.
key is an already open key, or any one of the predefined HKEY_* constants.
index is an integer that identifies the index of the value to retrieve.

The function retrieves the name of one subkey each time it is called.
It is typically called repeatedly, until an EnvironmentError exception
is raised, indicating no more values.

The result is a tuple of 3 items:
value_name is a string that identifies the value.
value_data is an object that holds the value data, and whose type depends
 on the underlying registry type.
data_type is an integer that identifies the type of the value data."""
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

                        return space.newtuple([
                            space.wrap(rffi.charp2str(valuebuf)),
                            convert_from_regdata(space, databuf,
                                                 retDataSize[0], retType[0]),
                            space.wrap(retType[0]),
                            ])
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

def EnumKey(space, w_hkey, index):
    """string = EnumKey(key, index) - Enumerates subkeys of an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
index is an integer that identifies the index of the key to retrieve.

The function retrieves the name of one subkey each time it is called.
It is typically called repeatedly until an EnvironmentError exception is
raised, indicating no more values are available."""
    hkey = hkey_w(w_hkey, space)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)

    # max key name length is 255
    buf = lltype.malloc(rffi.CCHARP.TO, 256, flavor='raw')
    try:
        retValueSize = lltype.malloc(rwin32.LPDWORD.TO, 1, flavor='raw')
        try:
            retValueSize[0] = 256 # includes NULL terminator
            ret = rwinreg.RegEnumKeyEx(hkey, index, buf, retValueSize,
                                       null_dword, None, null_dword,
                                       lltype.nullptr(rwin32.PFILETIME.TO))
            if ret != 0:
                raiseWindowsError(space, ret, 'RegEnumKeyEx')
            return space.wrap(rffi.charp2str(buf))
        finally:
            lltype.free(retValueSize, flavor='raw')
    finally:
        lltype.free(buf, flavor='raw')

EnumKey.unwrap_spec = [ObjSpace, W_Root, int]

def QueryInfoKey(space, w_hkey):
    """tuple = QueryInfoKey(key) - Returns information about a key.

key is an already open key, or any one of the predefined HKEY_* constants.

The result is a tuple of 3 items:
An integer that identifies the number of sub keys this key has.
An integer that identifies the number of values this key has.
A long integer that identifies when the key was last modified (if available)
 as 100's of nanoseconds since Jan 1, 1600."""
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
                return space.newtuple([space.wrap(nSubKeys[0]),
                                       space.wrap(nValues[0]),
                                       space.wrap(l)])
            finally:
                lltype.free(ft, flavor='raw')
        finally:
            lltype.free(nValues, flavor='raw')
    finally:
        lltype.free(nSubKeys, flavor='raw')
QueryInfoKey.unwrap_spec = [ObjSpace, W_Root]

def str_or_None_w(space, w_obj):
    if space.is_w(w_obj, space.w_None):
        return None
    return space.str_w(w_obj)

def ConnectRegistry(space, w_machine, w_hkey):
    """key = ConnectRegistry(computer_name, key)

Establishes a connection to a predefined registry handle on another computer.

computer_name is the name of the remote computer, of the form \\\\computername.
 If None, the local computer is used.
key is the predefined handle to connect to.

The return value is the handle of the opened key.
If the function fails, an EnvironmentError exception is raised."""
    machine = str_or_None_w(space, w_machine)
    hkey = hkey_w(w_hkey, space)
    rethkey = lltype.malloc(rwinreg.PHKEY.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegConnectRegistry(machine, hkey, rethkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegConnectRegistry')
        return space.wrap(W_HKEY(rethkey[0]))
    finally:
        lltype.free(rethkey, flavor='raw')
ConnectRegistry.unwrap_spec = [ObjSpace, W_Root, W_Root]
