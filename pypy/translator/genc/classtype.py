from __future__ import generators
from pypy.translator.genc.basetype import CType
from pypy.objspace.flow.model import SpaceOperation, Constant, Variable


class CClassPtrType(CType):
    error_return  = 'NULL'

    # For now, this is the singleton type "pointer to the class C"
    # It's supposed to become "pointer to class C or any subclass of C"

    def __init__(self, translator, classdef, instancetype):
        super(CClassPtrType, self).__init__(translator)
        self.classdef = classdef
        self.instancetype = instancetype
        self.typename = 'Kls' + instancetype.typename

    def nameof(self, cls, debug=None):
        assert cls is self.classdef.cls    # for now
        return '((%s)1)' % self.typename   # no class data at all

    def init_globals(self, genc):
        yield 'typedef void *%s;' % self.typename
        yield '#define OP_INCREF_%s(x)  /* nothing */' % self.typename
        yield '#define OP_DECREF_%s(x)  /* nothing */' % self.typename

    # ____________________________________________________________

    def spec_simple_call(self, typer, op):
        cinst = self.instancetype
        yield typer.typed_op(SpaceOperation('new_%s' % (cinst.typename,),
                                            [], op.result),   # args, ret
                                            [], cinst     )   # args_t, ret_t

        cls = self.classdef.cls
        init = getattr(cls, '__init__', None)
        if init is not None and init != object.__init__:
            raise Exception, "XXX not implemented"
