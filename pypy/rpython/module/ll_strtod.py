
import py
from pypy.rpython.extfunc import BaseLazyRegistering, extdef, registering
from pypy.rlib import rarithmetic
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.autopath import pypydir
from pypy.rpython.ootypesystem import ootype
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = ['src/ll_strtod.h'],
        separate_module_sources = ['#include <src/ll_strtod.h>'],
        export_symbols = ['LL_strtod_formatd', 'LL_strtod_parts_to_float'],
    )

class RegisterStrtod(BaseLazyRegistering):
    def __init__(self):
        self.configure(CConfig)
    
    @registering(rarithmetic.formatd)
    def register_formatd(self):
        ll_strtod = self.llexternal('LL_strtod_formatd',
                                    [rffi.CCHARP, rffi.DOUBLE], rffi.CCHARP,
                                    sandboxsafe=True, threadsafe=False)
        
        def llimpl(fmt, x):
            res = ll_strtod(fmt, x)
            return rffi.charp2str(res)

        def oofakeimpl(fmt, x):
            return ootype.oostring(rarithmetic.formatd(fmt._str, x), -1)

        return extdef([str, float], str, 'll_strtod.ll_strtod_formatd',
                      llimpl=llimpl, oofakeimpl=oofakeimpl,
                      sandboxsafe=True)

    @registering(rarithmetic.parts_to_float)
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
            return rarithmetic.parts_to_float(sign._str, beforept._str,
                                              afterpt._str, exponent._str)

        return extdef([str, str, str, str], float,
                      'll_strtod.ll_strtod_parts_to_float', llimpl=llimpl,
                      oofakeimpl=oofakeimpl, sandboxsafe=True)
