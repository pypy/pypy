"""
GenC-specific type specializer
"""

from __future__ import generators
from pypy.translator.typer import Specializer
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.annotation.model import SomeInteger, SomePBC, SomeTuple, SomeList
from pypy.translator.genc.pyobjtype import CPyObjectType
from pypy.translator.genc.inttype import CIntType
from pypy.translator.genc.nonetype import CNoneType
from pypy.translator.genc.functype import CFuncPtrType
from pypy.translator.genc.tupletype import CTupleType
from pypy.translator.genc.listtype import CListType
import types
from pypy.interpreter.pycode import CO_VARARGS

class GenCSpecializer(Specializer):

    def __init__(self, annotator):
        # instantiate the common concrete types
        t = annotator.translator
        self.TInt      = TInt      = t.getconcretetype(CIntType)
        self.TNone     = TNone     = t.getconcretetype(CNoneType)
        self.TPyObject = TPyObject = t.getconcretetype(CPyObjectType)

        # initialization
        Specializer.__init__(
            self, annotator,
            defaultconcretetype = TPyObject,

            # in more-specific-first, more-general-last order
            typematches = [TNone, TInt],

            specializationtable = [
                ## op         specialized op   arg types   concrete return type
                ('add',         'int_add',     TInt, TInt,   TInt),
                ('inplace_add', 'int_add',     TInt, TInt,   TInt),
                ('sub',         'int_sub',     TInt, TInt,   TInt),
                ('inplace_sub', 'int_sub',     TInt, TInt,   TInt),
                ('is_true',     'int_is_true', TInt,         TInt),
                ],
            )

    def annotation2concretetype(self, s_value):
        besttype = Specializer.annotation2concretetype(self, s_value)
        if besttype == self.defaultconcretetype:

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
                    besttype = self.annotator.translator.getconcretetype(
                        CFuncPtrType, tuple(args_ct), res_ct)

            elif isinstance(s_value, SomeTuple):
                items_ct = [self.annotation2concretetype(s_item)
                            for s_item in s_value.items]
                besttype = self.annotator.translator.getconcretetype(
                    CTupleType, tuple(items_ct))

            # -- DISABLED while it's incomplete
            #elif isinstance(s_value, SomeList):
            #    item_ct = self.annotation2concretetype(s_value.s_item)
            #    besttype = self.annotator.translator.getconcretetype(
            #        CListType, item_ct)

        return besttype

    def specialized_op(self, op, bindings):
        if op.opname in ('newtuple', 'newlist'):
            # operations that are controlled by their return type
            s_binding = self.annotator.binding(op.result, True)
        elif bindings:
            # operations are by default controlled by their 1st arg
            s_binding = bindings[0]
        else:
            s_binding = None

        if s_binding is not None:
            ct = self.annotation2concretetype(s_binding)
            meth = getattr(ct, 'spec_' + op.opname, None)
            if meth:
                try:
                    return meth(self, op)
                except NotImplementedError:
                    pass
        # fall-back
        return Specializer.specialized_op(self, op, bindings)


    def incref_op(self, v):
        vnone = Variable()
        vnone.concretetype = self.TNone
        return SpaceOperation('incref', [v], vnone)

    def deref_op(self, v):
        vnone = Variable()
        vnone.concretetype = self.TNone
        return SpaceOperation('decref', [v], vnone)
