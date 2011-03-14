
import py
from pypy.rpython.extfunc import BaseLazyRegistering, extdef, registering
from pypy.rlib import rfloat
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.autopath import pypydir
from pypy.rpython.ootypesystem import ootype
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir
from pypy.annotation.model import SomeString

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = ['src/ll_strtod.h'],
        include_dirs = [str(py.path.local(pypydir).join('translator', 'c'))],
        separate_module_sources = ['#include <src/ll_strtod.h>'],
        export_symbols = ['LL_strtod_formatd', 'LL_strtod_parts_to_float'],
    )

class RegisterStrtod(BaseLazyRegistering):
    def __init__(self):
        self.configure(CConfig)
    
    @registering(rfloat._formatd)
    def register_formatd(self):
        ll_strtod = self.llexternal('LL_strtod_formatd',
                                    [rffi.DOUBLE, rffi.CHAR, rffi.INT], rffi.CCHARP,
                                    sandboxsafe=True, threadsafe=False)

        # Like PyOS_double_to_string(), when PY_NO_SHORT_FLOAT_REPR is defined
        def llimpl(x, code, precision, flags):
            upper = False
            if code == 'r':
                code = 'g'
                precision = 17
            elif code == 'E':
                code = 'e'
                upper = True
            elif code == 'F':
                code = 'f'
                upper = True
            elif code == 'G':
                code = 'g'
                upper = True

            res = ll_strtod(x, code, precision)
            s = rffi.charp2str(res)

            if flags & rfloat.DTSF_ADD_DOT_0:
                s = ensure_decimal_point(s, precision)

            # Add sign when requested
            if flags & rfloat.DTSF_SIGN and s[0] != '-':
                s = '+' + s

            # Convert to upper case
            if upper:
                s = s.upper()

            return s

        def oofakeimpl(x, code, precision, flags):
            return ootype.oostring(rfloat.formatd(x, code, precision, flags), -1)

        return extdef([float, lltype.Char, int, int],
                      SomeString(can_be_None=True),
                      'll_strtod.ll_strtod_formatd',
                      llimpl=llimpl, oofakeimpl=oofakeimpl,
                      sandboxsafe=True)

    @registering(rfloat.parts_to_float)
    def register_parts_to_float(self):
        ll_parts_to_float = self.llexternal('LL_strtod_parts_to_float',
                                            [rffi.CCHARP] * 4, rffi.DOUBLE,
                                            sandboxsafe=True,
                                            threadsafe=False)

        def llimpl(sign, beforept, afterpt, exponent):
            res = ll_parts_to_float(sign, beforept, afterpt, exponent)
            if res == -1 and rposix.get_errno() == 42:
                raise ValueError("Wrong literal for float")
            return res

        def oofakeimpl(sign, beforept, afterpt, exponent):
            return rfloat.parts_to_float(sign._str, beforept._str,
                                         afterpt._str, exponent._str)

        tp = SomeString(can_be_None=True)
        return extdef([tp, tp, tp, tp], float,
                      'll_strtod.ll_strtod_parts_to_float', llimpl=llimpl,
                      oofakeimpl=oofakeimpl, sandboxsafe=True)

def ensure_decimal_point(s, precision):
    # make sure we have at least one character after the decimal point (and
    # make sure we have a decimal point); also switch to exponential notation
    # in some edge cases where the extra character would produce more
    # significant digits that we really want.

    pos = s.find('.')
    if pos >= 0:
        if pos + 1 < len(s) and s[pos + 1].isdigit():
            # Nothing to do, we already have a decimal point
            # and a digit after it
            pass
        else:
            # Normally not used
            s += '0'
    else:
        pos = s.find('e')
        if pos >= 0:
            # Don't add ".0" if we have an exponent
            pass
        else:
            s += '.0'

    return s
