
import types
from pypy.annotation import model as annmodel

class Sig(object):

    def __init__(self, *argtypes):
        self.argtypes = argtypes
        
    def __call__(self, funcdesc, inputcells):
        from pypy.rpython.lltypesystem import lltype
        args_s = []
        for i, argtype in enumerate(self.argtypes):
            if isinstance(argtype, (types.FunctionType, types.MethodType)):
                argtype = argtype(*inputcells)
            if isinstance(argtype, annmodel.SomeObject):
                args_s.append(argtype)
            elif isinstance(argtype, lltype.LowLevelType):
                if argtype is lltype.Void:
                    # XXX the mapping between Void and annotation
                    # is not quite well defined
                    s_input = inputcells[i]
                    assert isinstance(s_input, annmodel.SomePBC)
                    assert s_input.is_constant()
                    args_s.append(s_input)
                else:
                    args_s.append(annmodel.lltype_to_annotation(argtype))
            else:
                args_s.append(funcdesc.bookkeeper.valueoftype(argtype))
        if len(inputcells) != len(args_s):
            raise Exception("%r: expected %d args, got %d" % (funcdesc,
                                                              len(args_s),
                                                              len(inputcells)))
        for i, (s_arg, s_input) in enumerate(zip(args_s, inputcells)):
            if not s_arg.contains(s_input):
                raise Exception("%r argument %d:\n"
                                "expected %s,\n"
                                "     got %s" % (funcdesc, i+1,
                                             s_arg,
                                             s_input))
        inputcells[:] = args_s
