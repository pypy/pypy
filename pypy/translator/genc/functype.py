from __future__ import generators
from pypy.translator.genc.basetype import CType


class CFuncPtrType(CType):
    error_return = 'NULL'

    Counter = 0

    def __init__(self, translator, argtypes, returntype):
        super(CFuncPtrType, self).__init__(translator)
        self.argtypes = argtypes
        self.returntype = returntype
        self.typename = 'funcptr%d' % CFuncPtrType.Counter
        CFuncPtrType.Counter += 1

    def debugname(self):
        # a nice textual name for debugging...
        argnames = [ct.debugname() for ct in self.argtypes]
        returnname = self.returntype.debugname()
        return 'fn(%s) -> %s' % (', '.join(argnames), returnname)

    def nameof(self, func, debug=None):
        return self.genc().getfuncdef(func).fast_name

    def init_globals(self, genc):
        # build a type declaration template matching the C syntax
        # for function pointer types:
        #    <returntype> (*<name_to_insert_here>) (<argument types>)
        arglist = [ct.typename for ct in self.argtypes]
        argtemplate = ', '.join(arglist or ['void'])
        yield "typedef %s (*%s) (%s);" % (self.returntype.typename,
                                          self.typename,
                                          argtemplate)
        yield genc.loadincludefile('func_template.h') % {
            'typename': self.typename,
            }

    def spec_simple_call(self, typer, op):
        argtypes = [self]
        argtypes += self.argtypes
        yield typer.typed_op(op, argtypes, self.returntype,
                             newopname='direct_call')
