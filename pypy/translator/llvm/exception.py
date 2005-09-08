class ExceptionPolicy:
    def __init__(self):
        raise Exception, 'ExceptionPolicy should not be used directly'

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

    def llc_options(self):
        return '-enable-correct-eh-support'


class FastExceptionPolicy(ExceptionPolicy):    #uses only 'direct' exception class comparision
    def __init__(self):
        pass

    def llc_options(self):
        return '-enable-correct-eh-support'
