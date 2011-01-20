from __future__ import with_statement
from pypy.rlib import rarithmetic
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstring import StringBuilder
import py

cdir = py.path.local(pypydir) / 'translator' / 'c'
include_dirs = [cdir]

eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    libraries = [],
    separate_module_files = [cdir / 'src' / 'dtoa.c'],
    separate_module_sources = ['''
       #include <stdlib.h>
       #include <assert.h>
       #include "src/allocator.h"
    '''],
    export_symbols = ['_PyPy_dg_strtod',
                      '_PyPy_dg_dtoa',
                      '_PyPy_dg_freedtoa',
                      ],
    )

dg_strtod = rffi.llexternal(
    '_PyPy_dg_strtod', [rffi.CCHARP, rffi.CCHARPP], rffi.DOUBLE,
    compilation_info=eci)

dg_dtoa = rffi.llexternal(
    '_PyPy_dg_dtoa', [rffi.DOUBLE, rffi.INT, rffi.INT,
                    rffi.INTP, rffi.INTP, rffi.CCHARPP], rffi.CCHARP,
    compilation_info=eci)

dg_freedtoa = rffi.llexternal(
    '_PyPy_dg_freedtoa', [rffi.CCHARP], lltype.Void,
    compilation_info=eci)

def strtod(input):
    with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as end_ptr:
        with rffi.scoped_str2charp(input) as ll_input:
            result = dg_strtod(ll_input, end_ptr)
            if end_ptr[0] and ord(end_ptr[0][0]):
                offset = (rffi.cast(rffi.LONG, end_ptr[0]) -
                          rffi.cast(rffi.LONG, ll_input))
                raise ValueError("invalid input at position %d" % (offset,))
            return result

def dtoa(value, mode=0, precision=0, flags=0):
    builder = StringBuilder(20)
    with lltype.scoped_alloc(rffi.INTP.TO, 1) as decpt_ptr:
        with lltype.scoped_alloc(rffi.INTP.TO, 1) as sign_ptr:
            with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as end_ptr:
                output_ptr = dg_dtoa(value, mode, precision,
                                     decpt_ptr, sign_ptr, end_ptr)
                try:
                    if sign_ptr[0] == 1:
                        builder.append('-')
                    elif flags & rarithmetic.DTSF_SIGN:
                        builder.append('+')
                    buflen = (rffi.cast(rffi.LONG, end_ptr[0]) -
                              rffi.cast(rffi.LONG, output_ptr))
                    intpart = rffi.cast(lltype.Signed, decpt_ptr[0])
                    if intpart <= buflen:
                        builder.append(rffi.charpsize2str(output_ptr, intpart))
                    else:
                        builder.append(rffi.charpsize2str(output_ptr, buflen))
                        while buflen < intpart:
                            builder.append('0')
                            intpart -= 1
                    fracpart = buflen - intpart
                    if fracpart > 0:
                        builder.append('.')
                        ptr = rffi.ptradd(output_ptr, intpart)
                        builder.append(rffi.charpsize2str(ptr, fracpart))
                    elif flags & rarithmetic.DTSF_ADD_DOT_0:
                        builder.append('.0')
                finally:
                    dg_freedtoa(output_ptr)
    return builder.build()

def llimpl_strtod(value, code, precision, flags):
    if code in 'EFG':
        code = code.lower()

    if code == 'e':
        mode = 2
        precision += 1
    elif code == 'f':
        mode = 3
    elif code == 'g':
        mode = 2
        # precision 0 makes no sense for 'g' format; interpret as 1
        if precision == 0:
            precision = 1
    elif code == 'r':
        # repr format
        mode = 0
        assert precision == 0
    else:
        raise ValueError('Invalid mode')

    return dtoa(value, mode=mode, precision=precision, flags=flags)
