from pypy.translator.genc.parametric import parametrictype


class CType_FuncPtr:
    __metaclass__ = parametrictype

    def __initsubclass__(cls, key):
        cls.args_typecls = key[:-1]
        cls.return_typecls = key[-1]
        arglist = [tc.ctypetemplate % ('',) for tc in cls.args_typecls]
        argtemplate = ', '.join(arglist or ['void'])
        header = '(*%s)(' + argtemplate + ')'
        cls.ctypetemplate = cls.return_typecls.ctypetemplate % (header,)

    def __init__(self, genc):
        self.genc = genc

    def nameof(self, func, debug=None):
        return self.genc.getfuncdef(func).fast_name
