"""
GenC-specific type specializer
"""

from pypy.translator.typer import Specializer, TypeMatch
from pypy.annotation.model import SomeInteger, SomePBC
from pypy.translator.genc.t_pyobj import CType_PyObject
from pypy.translator.genc.t_int import CType_Int, CType_None
from pypy.translator.genc.t_func import CType_FuncPtr
import types
from pypy.interpreter.pycode import CO_VARARGS

class GenCSpecializer(Specializer):

    TInt  = TypeMatch(SomeInteger(), CType_Int)
    TNone = TypeMatch(SomePBC({None: True}), CType_None)

    # in more-specific-first, more-general-last order
    typematches = [TNone, TInt]

    defaulttypecls = CType_PyObject

    specializationtable = [
        ## op         specialized op   arg types   concrete return type
        ('add',         'int_add',     TInt, TInt,   CType_Int),
        ('inplace_add', 'int_add',     TInt, TInt,   CType_Int),
        ('sub',         'int_sub',     TInt, TInt,   CType_Int),
        ('inplace_sub', 'int_sub',     TInt, TInt,   CType_Int),
        ('is_true',     'int_is_true', TInt,         CType_Int),
        ]

    def annotation2typecls(self, s_value):
        besttype = Specializer.annotation2typecls(self, s_value)
        if besttype is None:

            if isinstance(s_value, SomePBC):
                # XXX! must be somehow unified with bookkeeper.pycall()!
                # XXX  for now, we support the very simplest case only.
                if (s_value.is_constant() and
                    isinstance(s_value.const, types.FunctionType) and
                    not (s_value.const.func_code.co_flags & CO_VARARGS) and
                    s_value.const in self.annotator.translator.flowgraphs):
                    
                    graph = self.annotator.translator.flowgraphs[s_value.const]
                    args_ct = [self.setbesttype(a) for a in graph.getargs()]
                    res_ct = self.setbesttype(graph.getreturnvar())
                    key = tuple(args_ct + [res_ct])
                    besttype = CType_FuncPtr[key]

        return besttype

    def getspecializedop(self, op, bindings):
        if op.opname == 'simple_call':
            s_callable = self.annotator.binding(op.args[0], True)
            if s_callable is not None:
                ct = self.annotation2typecls(s_callable)
                if ct is not None and issubclass(ct, CType_FuncPtr):
                    args_typecls = [ct]
                    args_typecls += ct.args_typecls
                    return 'direct_call', args_typecls, ct.return_typecls

        return Specializer.getspecializedop(self, op, bindings)
