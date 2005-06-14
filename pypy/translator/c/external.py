from __future__ import generators
from pypy.rpython.lltype import typeOf, Void
from pypy.translator.c.support import cdecl, ErrorValue, somelettersfrom


class CExternalFunctionCodeGenerator:

    def __init__(self, fnptr, db):
        self.fnptr = fnptr
        self.db = db
        self.FUNCTYPE = typeOf(fnptr)
        assert Void not in self.FUNCTYPE.ARGS
        self.argtypenames = [db.gettype(T) for T in self.FUNCTYPE.ARGS]
        self.resulttypename = db.gettype(self.FUNCTYPE.RESULT)

    def argnames(self):
        return ['%s%d' % (somelettersfrom(self.argtypenames[i]), i)
                for i in range(len(self.argtypenames))]

    def allconstantvalues(self):
        return []

    def cfunction_declarations(self):
        if self.FUNCTYPE.RESULT != Void:
            yield '%s;' % cdecl(self.resulttypename, 'result')

    def cfunction_body(self):
        call = '%s(%s)' % (self.fnptr._name, ', '.join(self.argnames()))
        if self.FUNCTYPE.RESULT != Void:
            yield 'result = %s;' % call
            yield 'if (PyErr_Occurred()) ConvertExceptionFromCPython();'
            yield 'return result;'
        else:
            yield '%s;' % call
            yield 'if (PyErr_Occurred()) ConvertExceptionFromCPython();'
