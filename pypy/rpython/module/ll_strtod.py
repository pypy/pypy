
import py
from pypy.rpython.extfunc import BaseLazyRegistering, extdef, registering
from pypy.rlib import rarithmetic
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import cache_c_module
from pypy.tool.autopath import pypydir
from pypy.rpython.ootypesystem import ootype

class CConfig:
    _includes_ = ['src/ll_strtod.h']

class RegisterStrtod(BaseLazyRegistering):
    def __init__(self):
        # HACK HACK HACK
        # we need to have some sane way of doing stuff below
        # problem: we don't have a way to call things in our header files
        from pypy.tool.udir import udir
        c_file = udir.join('test_strtod.c')
        c_file.write(py.code.Source("""
        #include <src/ll_strtod.h>
        """))
        cache_c_module([c_file], '_ll_strtod')
        self._libraries_ = [str(py.path.local(pypydir).join('_cache',
                                                            '_ll_strtod.so'))]
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
            if res == -1 and rffi.get_errno() == 42:
                raise ValueError("Wrong literal for float")
            return res

        def oofakeimpl(sign, beforept, afterpt, exponent):
            return rarithmetic.parts_to_float(sign._str, beforept._str,
                                              afterpt._str, exponent._str)

        return extdef([str, str, str, str], float,
                      'll_strtod.ll_strtod_parts_to_float', llimpl=llimpl,
                      oofakeimpl=oofakeimpl, sandboxsafe=True)
