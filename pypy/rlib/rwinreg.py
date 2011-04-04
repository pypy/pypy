from __future__ import with_statement
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform as platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import rwin32

eci = ExternalCompilationInfo(
    includes = ['windows.h',
                ],
    libraries = ('Advapi32', 'kernel32')
    )
class CConfig:
    _compilation_info_ = eci


constant_names = '''
KEY_QUERY_VALUE KEY_SET_VALUE KEY_CREATE_SUB_KEY KEY_ENUMERATE_SUB_KEYS
KEY_NOTIFY KEY_CREATE_LINK KEY_READ KEY_WRITE KEY_EXECUTE KEY_ALL_ACCESS
KEY_WOW64_64KEY KEY_WOW64_32KEY REG_OPTION_RESERVED REG_OPTION_NON_VOLATILE
REG_OPTION_VOLATILE REG_OPTION_CREATE_LINK REG_OPTION_BACKUP_RESTORE
REG_OPTION_OPEN_LINK REG_LEGAL_OPTION REG_CREATED_NEW_KEY
REG_OPENED_EXISTING_KEY REG_WHOLE_HIVE_VOLATILE REG_REFRESH_HIVE
REG_NO_LAZY_FLUSH REG_NOTIFY_CHANGE_NAME REG_NOTIFY_CHANGE_ATTRIBUTES
REG_NOTIFY_CHANGE_LAST_SET REG_NOTIFY_CHANGE_SECURITY REG_LEGAL_CHANGE_FILTER
REG_NONE REG_SZ REG_EXPAND_SZ REG_BINARY REG_DWORD REG_DWORD_LITTLE_ENDIAN
REG_DWORD_BIG_ENDIAN REG_LINK REG_MULTI_SZ REG_RESOURCE_LIST
REG_FULL_RESOURCE_DESCRIPTOR REG_RESOURCE_REQUIREMENTS_LIST

HKEY_LOCAL_MACHINE HKEY_CLASSES_ROOT HKEY_CURRENT_CONFIG HKEY_CURRENT_USER
HKEY_DYN_DATA HKEY_LOCAL_MACHINE HKEY_PERFORMANCE_DATA HKEY_USERS

ERROR_MORE_DATA
'''.split()
for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

constants = {}
cConfig = platform.configure(CConfig)
constants.update(cConfig)
globals().update(cConfig)

def external(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci,
                           calling_conv='win')

HKEY = rwin32.HANDLE
PHKEY = rffi.CArrayPtr(HKEY)
REGSAM = rwin32.DWORD

RegSetValue = external(
    'RegSetValueA',
    [HKEY, rffi.CCHARP, rwin32.DWORD, rffi.CCHARP, rwin32.DWORD],
    rffi.LONG)

RegSetValueEx = external(
    'RegSetValueExA',
    [HKEY, rffi.CCHARP, rwin32.DWORD,
     rwin32.DWORD, rffi.CCHARP, rwin32.DWORD],
    rffi.LONG)

RegQueryValue = external(
    'RegQueryValueA',
    [HKEY, rffi.CCHARP, rffi.CCHARP, rwin32.PLONG],
    rffi.LONG)

RegQueryValueEx = external(
    'RegQueryValueExA',
    [HKEY, rffi.CCHARP, rwin32.LPDWORD, rwin32.LPDWORD,
     rffi.CCHARP, rwin32.LPDWORD],
    rffi.LONG)

RegCreateKey = external(
    'RegCreateKeyA',
    [HKEY, rffi.CCHARP, PHKEY],
    rffi.LONG)

RegCreateKeyEx = external(
    'RegCreateKeyExA',
    [HKEY, rffi.CCHARP, rwin32.DWORD, rffi.CCHARP, rwin32.DWORD,
     REGSAM, rffi.VOIDP, PHKEY, rwin32.LPDWORD],
    rffi.LONG)

RegDeleteValue = external(
    'RegDeleteValueA',
    [HKEY, rffi.CCHARP],
    rffi.LONG)

RegDeleteKey = external(
    'RegDeleteKeyA',
    [HKEY, rffi.CCHARP],
    rffi.LONG)

RegOpenKeyEx = external(
    'RegOpenKeyExA',
    [HKEY, rffi.CCHARP, rwin32.DWORD, REGSAM, PHKEY],
    rffi.LONG)

RegEnumValue = external(
    'RegEnumValueA',
    [HKEY, rwin32.DWORD, rffi.CCHARP,
     rwin32.LPDWORD, rwin32.LPDWORD, rwin32.LPDWORD,
     rffi.CCHARP, rwin32.LPDWORD],
    rffi.LONG)

RegEnumKeyEx = external(
    'RegEnumKeyExA',
    [HKEY, rwin32.DWORD, rffi.CCHARP,
     rwin32.LPDWORD, rwin32.LPDWORD,
     rffi.CCHARP, rwin32.LPDWORD, rwin32.PFILETIME],
    rffi.LONG)

RegQueryInfoKey = external(
    'RegQueryInfoKeyA',
    [HKEY, rffi.CCHARP, rwin32.LPDWORD, rwin32.LPDWORD,
     rwin32.LPDWORD, rwin32.LPDWORD, rwin32.LPDWORD,
     rwin32.LPDWORD, rwin32.LPDWORD, rwin32.LPDWORD,
     rwin32.LPDWORD, rwin32.PFILETIME],
    rffi.LONG)

RegCloseKey = external(
    'RegCloseKey',
    [HKEY],
    rffi.LONG)

RegFlushKey = external(
    'RegFlushKey',
    [HKEY],
    rffi.LONG)

RegLoadKey = external(
    'RegLoadKeyA',
    [HKEY, rffi.CCHARP, rffi.CCHARP],
    rffi.LONG)

RegSaveKey = external(
    'RegSaveKeyA',
    [HKEY, rffi.CCHARP, rffi.VOIDP],
    rffi.LONG)

RegConnectRegistry = external(
    'RegConnectRegistryA',
    [rffi.CCHARP, HKEY, PHKEY],
    rffi.LONG)

_ExpandEnvironmentStringsW = external(
    'ExpandEnvironmentStringsW',
    [rffi.CWCHARP, rffi.CWCHARP, rwin32.DWORD],
    rwin32.DWORD)

def ExpandEnvironmentStrings(source):
    with rffi.scoped_unicode2wcharp(source) as src_buf:
        size = _ExpandEnvironmentStringsW(src_buf,
                                          lltype.nullptr(rffi.CWCHARP.TO), 0)
        if size == 0:
            raise rwin32.lastWindowsError("ExpandEnvironmentStrings")
        size = intmask(size)
        with rffi.scoped_alloc_unicodebuffer(size) as dest_buf:
            if _ExpandEnvironmentStringsW(src_buf,
                                          dest_buf.raw, size) == 0:
                raise rwin32.lastWindowsError("ExpandEnvironmentStrings")
            return dest_buf.str(size - 1) # remove trailing \0
