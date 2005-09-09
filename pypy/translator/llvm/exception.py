from pypy.translator.llvm.codewriter import DEFAULT_CCONV


class ExceptionPolicy:
    def __init__(self):
        raise Exception, 'ExceptionPolicy should not be used directly'

    def pyrex_entrypoint_code(self, entrynode):
        return ''

    def llc_options(self):
        return ''

    def new(exceptionpolicy=None):  #factory
        if exceptionpolicy is None or exceptionpolicy == 'cpython':
            from pypy.translator.llvm.exception import CPythonExceptionPolicy
            exceptionpolicy = CPythonExceptionPolicy()
        elif exceptionpolicy == 'fast':
            from pypy.translator.llvm.exception import FastExceptionPolicy
            exceptionpolicy = FastExceptionPolicy()
        elif exceptionpolicy == 'none':
            from pypy.translator.llvm.exception import NoneExceptionPolicy
            exceptionpolicy = NoneExceptionPolicy()
        else:
            raise Exception, 'unknown exceptionpolicy: ' + str(exceptionpolicy)
        return exceptionpolicy
    new = staticmethod(new)


class NoneExceptionPolicy(ExceptionPolicy):
    def __init__(self):
        pass


class CPythonExceptionPolicy(ExceptionPolicy):  #uses issubclass()
    def __init__(self):
        pass

    def pyrex_entrypoint_code(self, entrynode):
        returntype, entrypointname =  entrynode.getdecl().split('%', 1)
        if returntype == 'double ':
            noresult = '0.0'
        elif returntype == 'bool ':
            noresult = 'false'
        else:
            noresult = '0'
        cconv = DEFAULT_CCONV
        return '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    %%result = invoke %(cconv)s %(returntype)s%%%(entrypointname)s to label %%no_exception except label %%exception

no_exception:
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    ret %(returntype)s %%result

exception:
    ret %(returntype)s %(noresult)s
}

ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}
''' % locals()

    def llc_options(self):
        return '-enable-correct-eh-support'


class FastExceptionPolicy(ExceptionPolicy):    #uses only 'direct' exception class comparision
    def __init__(self):
        pass

    pyrex_entrypoint_code = CPythonExceptionPolicy.pyrex_entrypoint_code
    llc_options = CPythonExceptionPolicy.llc_options
