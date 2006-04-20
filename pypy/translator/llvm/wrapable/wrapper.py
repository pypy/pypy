from ctypes import c_int


class Wrapper(c_int):   #c_int because it needs to be a ctypes datatype for from_param to work
    def from_param(cls, p):
        try:
            return p.instance
        except:
            #XXX This might happen if we use a staticmethod (factory) to create a function.
            #    In that case we have no 'self' to store the instance in.
            #    An example of this can be found in wrap_llvm.py/ExecutionEngine.create
            return p
    from_param = classmethod(from_param)

    #def errcheck(retval, function, arguments):
    #    print 'Wrapper.errcheck: retval(instance)=%s, function=%s %s, arguments=%s' % (retval,function,dir(function.__class__),arguments)
    #    self.instance = retval
    #    return retval
    #errcheck = staticmethod(errcheck)
