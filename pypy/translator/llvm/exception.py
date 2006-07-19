
def _noresult(returntype):
    r = returntype.strip()
    if r == 'void':
        return 'void'
    elif r == 'bool':
        return 'bool false'
    elif r in 'float double'.split():
        return r + ' 0.0'
    elif r in 'ubyte sbyte ushort short uint int ulong long'.split():
        return r + ' 0'
    return r + ' null'

def llvm_implcode(entrynode):
    from pypy.translator.llvm.codewriter import DEFAULT_CCONV as cconv
    from pypy.translator.llvm.module.excsupport import exctransform_code
    returntype, entrypointname = entrynode.getdecl().split('%', 1)
    noresult = _noresult(returntype)
    return exctransform_code % locals()

