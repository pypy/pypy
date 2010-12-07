from __future__ import with_statement
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rstring import StringBuilder
import py

includes = []
libraries = []

cdir = py.path.local(pypydir) / 'translator' / 'c'
files = [cdir / 'src' / 'dtoa.c']
include_dirs = [cdir]

eci = ExternalCompilationInfo(
    include_dirs = include_dirs,
    libraries = libraries,
    separate_module_files = files,
    separate_module_sources = ['''
        #include <stdlib.h>
        #include <assert.h>
        #define WITH_PYMALLOC
        #include "src/obmalloc.c"
    '''],
    export_symbols = ['_Py_dg_strtod',
                      '_Py_dg_dtoa',
                      '_Py_dg_freedtoa',
                      ],
)

dg_strtod = rffi.llexternal(
    '_Py_dg_strtod', [rffi.CCHARP, rffi.CCHARPP], rffi.DOUBLE,
    compilation_info=eci)

dg_dtoa = rffi.llexternal(
    '_Py_dg_dtoa', [rffi.DOUBLE, rffi.INT, rffi.INT,
                    rffi.INTP, rffi.INTP, rffi.CCHARPP], rffi.CCHARP,
    compilation_info=eci)

dg_freedtoa = rffi.llexternal(
    '_Py_dg_freedtoa', [rffi.CCHARP], lltype.Void,
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

def dtoa(value):
    mode = 2
    precision = 3
    builder = StringBuilder(20)
    with lltype.scoped_alloc(rffi.INTP.TO, 1) as decpt_ptr:
        with lltype.scoped_alloc(rffi.INTP.TO, 1) as sign_ptr:
            with lltype.scoped_alloc(rffi.CCHARPP.TO, 1) as end_ptr:
                output_ptr = dg_dtoa(value, mode, precision,
                                     decpt_ptr, sign_ptr, end_ptr)
                buflen = (rffi.cast(rffi.LONG, end_ptr[0]) -
                          rffi.cast(rffi.LONG, output_ptr))
                builder.append(rffi.charpsize2str(output_ptr, decpt_ptr[0]))
                builder.append('.')
                ptr = rffi.ptradd(output_ptr, decpt_ptr[0])
                buflen -= decpt_ptr[0]
                builder.append(rffi.charpsize2str(ptr, buflen))
                dg_freedtoa(output_ptr)
    return builder.build()

def test_strtod():
    assert strtod("12345") == 12345.0
    assert strtod("1.1") == 1.1
    raises(ValueError, strtod, "123A")

def test_dtoa():
    assert dtoa(3.47) == "3.47"
    assert dtoa(1.1) == "1.1"
