"""Annotation and rtyping support for the result of os.stat(), os.lstat()
and os.fstat().  In RPython like in plain Python the stat result can be
indexed like a tuple but also exposes the st_xxx attributes.
"""
import os, sys
from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython import extregistry
from pypy.rpython.extfunc import register_external
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.lltypesystem.rtupletype import TUPLE_TYPE
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo

# XXX on Windows, stat() is flawed; see CPython's posixmodule.c for
# an implementation based on the Win32 API

# NOTE: float times are disabled for now, for simplicity.  They make the life
# of OO backends more complicated because for them we try to not depend on
# the details of the platform on which we do the translation.  Also, they
# seem not essential because they are disabled by default in CPython.
TIMESPEC = None
ModTime = lltype.Signed

# all possible fields - some of them are not available on all platforms
ALL_STAT_FIELDS = [
    ("st_mode",      lltype.Signed),
    ("st_ino",       lltype.SignedLongLong),
    ("st_dev",       lltype.SignedLongLong),
    ("st_nlink",     lltype.Signed),
    ("st_uid",       lltype.Signed),
    ("st_gid",       lltype.Signed),
    ("st_size",      lltype.SignedLongLong),
    ("st_atime",     ModTime),
    ("st_mtime",     ModTime),
    ("st_ctime",     ModTime),
    ("st_blksize",   lltype.Signed),
    ("st_blocks",    lltype.Signed),
    ("st_rdev",      lltype.Signed),
    ("st_flags",     lltype.Signed),
    #("st_gen",       lltype.Signed),     -- new in CPy 2.5, not implemented
    #("st_birthtime", ModTime),           -- new in CPy 2.5, not implemented
    ]
N_INDEXABLE_FIELDS = 10

# for now, check the host Python to know which st_xxx fields exist
STAT_FIELDS = [(_name, _TYPE) for (_name, _TYPE) in ALL_STAT_FIELDS
                              if hasattr(os.stat_result, _name)]

STAT_FIELD_TYPES = dict(STAT_FIELDS)      # {'st_xxx': TYPE}

STAT_FIELD_NAMES = [_name for (_name, _TYPE) in ALL_STAT_FIELDS
                          if _name in STAT_FIELD_TYPES]

def _expand(lst, originalname, timespecname):
    if TIMESPEC is not None:
        XXX # code not used right now
        for i, (_name, _TYPE) in enumerate(lst):
            if _name == originalname:
                # replace the 'st_atime' field of type rffi.DOUBLE
                # with a field 'st_atim' of type 'struct timespec'
                lst[i] = (timespecname, TIMESPEC.TO)
                break

LL_STAT_FIELDS = STAT_FIELDS[:]
_expand(LL_STAT_FIELDS, 'st_atime', 'st_atim')
_expand(LL_STAT_FIELDS, 'st_mtime', 'st_mtim')
_expand(LL_STAT_FIELDS, 'st_ctime', 'st_ctim')

del _expand, _name, _TYPE

# For OO backends, expose only the portable fields (the first 10).
PORTABLE_STAT_FIELDS = STAT_FIELDS[:N_INDEXABLE_FIELDS]

# ____________________________________________________________
#
# Annotation support

class SomeStatResult(annmodel.SomeObject):
    knowntype = os.stat_result

    def rtyper_makerepr(self, rtyper):
        from pypy.rpython.module import r_os_stat
        return r_os_stat.StatResultRepr(rtyper)

    def rtyper_makekey_ex(self, rtyper):
        return self.__class__,

    def getattr(self, s_attr):
        assert s_attr.is_constant(), "non-constant attr name in getattr()"
        attrname = s_attr.const
        TYPE = STAT_FIELD_TYPES[attrname]
        return annmodel.lltype_to_annotation(TYPE)

    def _get_rmarshall_support_(self):     # for rlib.rmarshal
        # reduce and recreate stat_result objects from 10-tuples
        # (we ignore the extra values here for simplicity and portability)
        def stat_result_reduce(st):
            return (st[0], st[1], st[2], st[3], st[4],
                    st[5], st[6], st[7], st[8], st[9])
        def stat_result_recreate(tup):
            return make_stat_result(tup + extra_zeroes)
        s_reduced = annmodel.SomeTuple([annmodel.lltype_to_annotation(TYPE)
                                       for name, TYPE in PORTABLE_STAT_FIELDS])
        extra_zeroes = (0,) * (len(STAT_FIELDS) - len(PORTABLE_STAT_FIELDS))
        return s_reduced, stat_result_reduce, stat_result_recreate

class __extend__(pairtype(SomeStatResult, annmodel.SomeInteger)):
    def getitem((s_sta, s_int)):
        assert s_int.is_constant(), "os.stat()[index]: index must be constant"
        index = s_int.const
        assert 0 <= index < N_INDEXABLE_FIELDS, "os.stat()[index] out of range"
        name, TYPE = STAT_FIELDS[index]
        return annmodel.lltype_to_annotation(TYPE)

s_StatResult = SomeStatResult()

def make_stat_result(tup):
    """Turn a tuple into an os.stat_result object."""
    positional = tup[:N_INDEXABLE_FIELDS]
    kwds = {}
    for i, name in enumerate(STAT_FIELD_NAMES[N_INDEXABLE_FIELDS:]):
        kwds[name] = tup[N_INDEXABLE_FIELDS + i]
    return os.stat_result(positional, kwds)

class MakeStatResultEntry(extregistry.ExtRegistryEntry):
    _about_ = make_stat_result

    def compute_result_annotation(self, s_tup):
        return s_StatResult

    def specialize_call(self, hop):
        from pypy.rpython.module import r_os_stat
        return r_os_stat.specialize_make_stat_result(hop)

# ____________________________________________________________
#
# RFFI support

if sys.platform.startswith('win'):
    _name_struct_stat = '_stati64'
    INCLUDES = ['sys/types.h', 'sys/stat.h']
else:
    _name_struct_stat = 'stat'
    INCLUDES = ['sys/types.h', 'sys/stat.h', 'unistd.h']

compilation_info = ExternalCompilationInfo(
    pre_include_bits = ['#define _FILE_OFFSET_BITS 64'],
    includes = INCLUDES
)

from pypy.rpython.tool import rffi_platform as platform
class CConfig:
    # This must be set to 64 on some systems to enable large file support.
    _compilation_info_ = compilation_info
    STAT_STRUCT = platform.Struct('struct %s' % _name_struct_stat, LL_STAT_FIELDS)
config = platform.configure(CConfig)

STAT_STRUCT = lltype.Ptr(config['STAT_STRUCT'])

def build_stat_result(st):
    # only for LL backends
    if TIMESPEC is not None:
        atim = st.c_st_atim; atime = atim.c_tv_sec + 1E-9 * atim.c_tv_nsec
        mtim = st.c_st_mtim; mtime = mtim.c_tv_sec + 1E-9 * mtim.c_tv_nsec
        ctim = st.c_st_ctim; ctime = ctim.c_tv_sec + 1E-9 * ctim.c_tv_nsec
    else:
        atime = st.c_st_atime
        mtime = st.c_st_mtime
        ctime = st.c_st_ctime

    result = (st.c_st_mode,
              st.c_st_ino,
              st.c_st_dev,
              st.c_st_nlink,
              st.c_st_uid,
              st.c_st_gid,
              st.c_st_size,
              atime,
              mtime,
              ctime)

    if "st_blksize" in STAT_FIELD_TYPES: result += (st.c_st_blksize,)
    if "st_blocks"  in STAT_FIELD_TYPES: result += (st.c_st_blocks,)
    if "st_rdev"    in STAT_FIELD_TYPES: result += (st.c_st_rdev,)
    if "st_flags"   in STAT_FIELD_TYPES: result += (st.c_st_flags,)

    return make_stat_result(result)


def register_stat_variant(name):
    if sys.platform.startswith('win'):
        _functions = {'stat':  '_stati64',
                      'fstat': '_fstati64',
                      'lstat': '_stati64'}    # no lstat on Windows
        c_func_name = _functions[name]
    elif sys.platform.startswith('linux'):
        # because we always use _FILE_OFFSET_BITS 64 - this helps things work that are not a c compiler 
        _functions = {'stat':  'stat64',
                      'fstat': 'fstat64',
                      'lstat': 'lstat64'}
        c_func_name = _functions[name]
    else:
        c_func_name = name

    arg_is_path = (name != 'fstat')
    if arg_is_path:
        ARG1 = rffi.CCHARP
    else:
        ARG1 = rffi.INT
    os_mystat = rffi.llexternal(c_func_name, [ARG1, STAT_STRUCT], rffi.INT,
                                compilation_info=compilation_info)

    def os_mystat_llimpl(arg):
        stresult = lltype.malloc(STAT_STRUCT.TO, flavor='raw')
        try:
            if arg_is_path:
                arg = rffi.str2charp(arg)
            error = rffi.cast(rffi.LONG, os_mystat(arg, stresult))
            if arg_is_path:
                rffi.free_charp(arg)
            if error != 0:
                raise OSError(rposix.get_errno(), "os_?stat failed")
            return build_stat_result(stresult)
        finally:
            lltype.free(stresult, flavor='raw')

    def fakeimpl(arg):
        st = getattr(os, name)(arg)
        fields = [TYPE for fieldname, TYPE in LL_STAT_FIELDS]
        TP = TUPLE_TYPE(fields)
        ll_tup = lltype.malloc(TP.TO)
        for i, (fieldname, TYPE) in enumerate(LL_STAT_FIELDS):
            val = getattr(st, fieldname)
            rffi.setintfield(ll_tup, 'item%d' % i, int(val))
        return ll_tup

    if arg_is_path:
        s_arg = str
    else:
        s_arg = int
    register_external(getattr(os, name), [s_arg], s_StatResult,
                      "ll_os.ll_os_%s" % (name,),
                      llimpl=func_with_new_name(os_mystat_llimpl,
                                                'os_%s_llimpl' % (name,)),
                      llfakeimpl=func_with_new_name(fakeimpl,
                                                    'os_%s_fake' % (name,)))

# ____________________________________________________________
if 0:
    XXX - """
        disabled for now:
        error codes are different when returned from the Win32 API,
        which makes things a mess that I don't want to tackle now...
    """
    # The CRT of Windows has a number of flaws wrt. its stat() implementation:
    # - for when we implement subsecond resolution in RPython, time stamps
    #   would be restricted to second resolution
    # - file modification times suffer from forth-and-back conversions between
    #   UTC and local time
    # Therefore, we implement our own stat, based on the Win32 API directly.
    from pypy.rpython.tool import rffi_platform as platform

    assert len(STAT_FIELDS) == 10    # no extra fields on Windows
    FILETIME = rffi.CStruct('_FILETIME', ('dwLowDateTime', rffi.LONG),
                                         ('dwHighDateTime', rffi.LONG))
    class CConfig:
        GET_FILEEX_INFO_LEVELS = platform.SimpleType('GET_FILEEX_INFO_LEVELS',
                                                     rffi.INT)
        GetFileExInfoStandard = platform.ConstantInteger(
            'GetFileExInfoStandard')
        WIN32_FILE_ATTRIBUTE_DATA = platform.Struct(
            '_WIN32_FILE_ATTRIBUTE_DATA',
            [('dwFileAttributes', rffi.ULONG),
             ('nFileSizeHigh', rffi.ULONG),
             ('nFileSizeLow', rffi.ULONG),
             ('ftCreationTime', FILETIME),
             ('ftLastAccessTime', FILETIME),
             ('ftCreationTime', FILETIME)])

    globals().update(platform.configure(CConfig))

    GetFileAttributesEx = rffi.llexternal(
        'GetFileAttributesExA', [rffi.CCHARP,
                                 GET_FILEEX_INFO_LEVELS,
                                 lltype.Ptr(WIN32_FILE_ATTRIBUTE_DATA)],
        rffi.INT)

    def os_stat_llimpl(path):
        data = lltype.malloc(WIN32_FILE_ATTRIBUTE_DATA, flavor='raw')
        try:
            l_path = rffi.str2charp(path)
            res = GetFileAttributesEx(l_path, GetFileExInfoStandard, data)
            rffi.free_charp(l_path)
            if res == 0:
                # ignore the GetLastError() which is a number that we cannot
                # easily report...
                XXX
            YYY
        finally:
            lltype.free(data, flavor='raw')
