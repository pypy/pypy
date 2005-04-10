from pypy.translator.genc.t_simple import CType


class CFuncPtrType(CType):
    error_return = 'NULL'

    def __init__(self, translator, argtypes, returntype):
        super(CFuncPtrType, self).__init__(translator)
        self.argtypes = argtypes
        self.returntype = returntype
        # build a type declaration template matching the strange C syntax
        # for function pointer types:
        #    <returntype> (*<name_to_insert_here>) (<argument types>)
        # which becomes funny when <returntype> itself is a complex type;
        # in that case, the whole rest of the line, i.e. the "(*..)(...)",
        # is what should be inserted into the returntype's "%s".
        arglist = [ct.ctypetemplate % ('',) for ct in argtypes]
        argtemplate = ', '.join(arglist or ['void'])
        header = '(*%s)(' + argtemplate + ')'
        self.ctypetemplate = returntype.ctypetemplate % (header,)

    def debugname(self):
        # a nice textual name for debugging...
        argnames = [ct.debugname() for ct in self.argtypes]
        returnname = self.returntype.debugname()
        return 'fn(%s) -> %s' % (', '.join(argnames), returnname)

    def nameof(self, func, debug=None):
        return self.genc().getfuncdef(func).fast_name
