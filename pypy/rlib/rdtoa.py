from __future__ import with_statement
from pypy.rlib import rarithmetic
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import jit
from pypy.rlib.rstring import StringBuilder
import py

cdir = py.path.local(pypydir) / 'translator' / 'c'
include_dirs = [cdir]

eci = ExternalCompilationInfo(
    include_dirs = [cdir],
    includes = ['src/dtoa.h'],
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
    end_ptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
    try:
        ll_input = rffi.str2charp(input)
        try:
            result = dg_strtod(ll_input, end_ptr)
            if end_ptr[0] and ord(end_ptr[0][0]):
                offset = (rffi.cast(rffi.LONG, end_ptr[0]) -
                          rffi.cast(rffi.LONG, ll_input))
                raise ValueError("invalid input at position %d" % (offset,))
            return result
        finally:
            rffi.free_charp(ll_input)
    finally:
        lltype.free(end_ptr, flavor='raw')

def format_nonfinite(digits, sign, flags):
    "Format dtoa's output for nonfinite numbers"
    if digits[0] == 'i' or digits[0] == 'I':
        if sign == 1:
            return '-inf'
        elif flags & rarithmetic.DTSF_SIGN:
            return '+inf'
        else:
            return 'inf'
    elif digits[0] == 'n' or digits[0] == 'N':
        return 'nan'
    else:
        # shouldn't get here
        raise ValueError

@jit.dont_look_inside
def format_number(digits, buflen, sign, decpt, code, precision, flags):
    # We got digits back, format them.  We may need to pad 'digits'
    # either on the left or right (or both) with extra zeros, so in
    # general the resulting string has the form
    #
    # [<sign>]<zeros><digits><zeros>[<exponent>]
    #
    # where either of the <zeros> pieces could be empty, and there's a
    # decimal point that could appear either in <digits> or in the
    # leading or trailing <zeros>.
    #
    # Imagine an infinite 'virtual' string vdigits, consisting of the
    # string 'digits' (starting at index 0) padded on both the left
    # and right with infinite strings of zeros.  We want to output a
    # slice
    #
    # vdigits[vdigits_start : vdigits_end]
    #
    # of this virtual string.  Thus if vdigits_start < 0 then we'll
    # end up producing some leading zeros; if vdigits_end > digits_len
    # there will be trailing zeros in the output.  The next section of
    # code determines whether to use an exponent or not, figures out
    # the position 'decpt' of the decimal point, and computes
    # 'vdigits_start' and 'vdigits_end'.
    builder = StringBuilder(20)

    use_exp = False
    vdigits_end = buflen
    if code == 'e':
        use_exp = True
        vdigits_end = precision
    elif code == 'f':
        vdigits_end = decpt + precision
    elif code == 'g':
        if decpt <= -4:
            use_exp = True
        elif decpt > precision:
            use_exp = True
        elif flags & rarithmetic.DTSF_ADD_DOT_0 and decpt == precision:
            use_exp = True
        if flags & rarithmetic.DTSF_ALT:
            vdigits_end = precision
    elif code == 'r':
        #  convert to exponential format at 1e16.  We used to convert
        #  at 1e17, but that gives odd-looking results for some values
        #  when a 16-digit 'shortest' repr is padded with bogus zeros.
        #  For example, repr(2e16+8) would give 20000000000000010.0;
        #  the true value is 20000000000000008.0.
        if decpt <= -4 or decpt > 16:
            use_exp = True
    else:
        raise ValueError

    # if using an exponent, reset decimal point position to 1 and
    # adjust exponent accordingly.
    if use_exp:
        exp = decpt - 1
        decpt = 1
    else:
        exp = 0

    # ensure vdigits_start < decpt <= vdigits_end, or vdigits_start <
    # decpt < vdigits_end if add_dot_0_if_integer and no exponent
    if decpt <= 0:
        vdigits_start = decpt-1
    else:
        vdigits_start = 0
    if vdigits_end <= decpt:
        if not use_exp and flags & rarithmetic.DTSF_ADD_DOT_0:
            vdigits_end = decpt + 1
        else:
            vdigits_end = decpt

    # double check inequalities
    assert vdigits_start <= 0
    assert 0 <= buflen <= vdigits_end
    # decimal point should be in (vdigits_start, vdigits_end]
    assert vdigits_start < decpt <= vdigits_end

    if sign == 1:
        builder.append('-')
    elif flags & rarithmetic.DTSF_SIGN:
        builder.append('+')

    # note that exactly one of the three 'if' conditions is true, so
    # we include exactly one decimal point
    # 1. Zero padding on left of digit string
    if decpt <= 0:
        builder.append_multiple_char('0', decpt - vdigits_start)
        builder.append('.')
        builder.append_multiple_char('0', 0 - decpt)
    else:
        builder.append_multiple_char('0', 0 - vdigits_start)

    # 2. Digits, with included decimal point
    if 0 < decpt <= buflen:
        builder.append(rffi.charpsize2str(digits, decpt - 0))
        builder.append('.')
        ptr = rffi.ptradd(digits, decpt)
        builder.append(rffi.charpsize2str(ptr, buflen - decpt))
    else:
        builder.append(rffi.charpsize2str(digits, buflen))

    # 3. And zeros on the right
    if buflen < decpt:
        builder.append_multiple_char('0', decpt - buflen)
        builder.append('.')
        builder.append_multiple_char('0', vdigits_end - decpt)
    else:
        builder.append_multiple_char('0', vdigits_end - buflen)

    s = builder.build()

    # Delete a trailing decimal pt unless using alternative formatting.
    if not flags & rarithmetic.DTSF_ALT:
        last = len(s) - 1
        if last >= 0 and s[last] == '.':
            s = s[:last]

    # Now that we've done zero padding, add an exponent if needed.
    if use_exp:
        if exp >= 0:
            exp_str = str(exp)
            if len(exp_str) < 2:
                s += 'e+0' + exp_str
            else:
                s += 'e+' + exp_str
        else:
            exp_str = str(-exp)
            if len(exp_str) < 2:
                s += 'e-0' + exp_str
            else:
                s += 'e-' + exp_str

    return s

def dtoa(value, code='r', mode=0, precision=0, flags=0):
    decpt_ptr = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
    try:
        sign_ptr = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
        try:
            end_ptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
            try:
                digits = dg_dtoa(value, mode, precision,
                                     decpt_ptr, sign_ptr, end_ptr)
                try:
                    buflen = (rffi.cast(rffi.LONG, end_ptr[0]) -
                              rffi.cast(rffi.LONG, digits))
                    sign = rffi.cast(lltype.Signed, sign_ptr[0])

                    # Handle nan and inf
                    if buflen and not digits[0].isdigit():
                        return format_nonfinite(digits, sign, flags)

                    decpt = rffi.cast(lltype.Signed, decpt_ptr[0])

                    return format_number(digits, buflen, sign, decpt,
                                         code, precision, flags)

                finally:
                    dg_freedtoa(digits)
            finally:
                lltype.free(end_ptr, flavor='raw')
        finally:
            lltype.free(sign_ptr, flavor='raw')
    finally:
        lltype.free(decpt_ptr, flavor='raw')

def dtoa_formatd(value, code, precision, flags):
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

    return dtoa(value, code, mode=mode, precision=precision, flags=flags)
