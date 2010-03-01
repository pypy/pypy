
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    includes = ['ctype.h']
)

def external(name, args, result, **kwds):
        return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)

tolower = external('tolower', [lltype.Signed], lltype.Signed,
                                      oo_primitive='tolower')
isalnum = external('isalnum', [lltype.Signed], lltype.Signed,
                   oo_primitive='isalnum')
                   
