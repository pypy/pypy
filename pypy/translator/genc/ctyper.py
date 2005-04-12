"""
GenC-specific type specializer
"""

from __future__ import generators
from pypy.translator.typer import Specializer
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.annotation.model import SomeInteger, SomePBC, SomeTuple
from pypy.translator.genc.pyobjtype import CPyObjectType
from pypy.translator.genc.inttype import CIntType
from pypy.translator.genc.nonetype import CNoneType
from pypy.translator.genc.functype import CFuncPtrType
from pypy.translator.genc.tupletype import CTupleType
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

        return besttype

    def specialized_op(self, op, bindings):
        if op.opname == 'simple_call':
            s_callable = self.annotator.binding(op.args[0], True)
            if s_callable is not None:
                ct = self.annotation2concretetype(s_callable)
                if isinstance(ct, CFuncPtrType):
                    argtypes = [ct]
                    argtypes += ct.argtypes
                    yield self.typed_op(op, argtypes, ct.returntype,
                                        newopname='direct_call')
                    return

        if op.opname == 'newtuple':
            s_tuple = self.annotator.binding(op.result, True)
            if s_tuple is not None:
                ctup = self.annotation2concretetype(s_tuple)
                if isinstance(ctup, CTupleType):
                    TInt  = self.TInt
                    TNone = self.TNone
                    v2 = op.result
                    yield self.typed_op(SpaceOperation('tuple_new', [], v2),
                                                                    [], ctup)
                    for i in range(len(ctup.itemtypes)):
                        vitem = op.args[i]
                        ct = ctup.itemtypes[i]
                        v0 = Variable()
                        yield self.typed_op(SpaceOperation('tuple_setitem',
                                   [v2,   Constant(i), vitem], v0),  # args, ret
                                   [ctup, TInt,        ct   ], TNone) # a_t, r_t
                        yield self.incref_op(vitem)
                    return

        if op.opname == 'getitem':
            s_obj = self.annotator.binding(op.args[0], True)
            if s_obj is not None:
                ctup = self.annotation2concretetype(s_obj)
                if isinstance(ctup, CTupleType):
                    if isinstance(op.args[1], Constant):
                        index = op.args[1].value
                        try:
                            ct = ctup.itemtypes[index]
                        except IndexError:
                            print "*** getitem: IndexError in tuple access"
                        else:
                            yield self.typed_op(op, [ctup, self.TInt], ct,
                                                newopname='tuple_getitem')
                            yield self.incref_op(op.result)
                            return

        # fall-back
        yield Specializer.specialized_op(self, op, bindings)


    def incref_op(self, v):
        vnone = Variable()
        vnone.concretetype = self.TNone
        return SpaceOperation('incref', [v], vnone)

    def deref_op(self, v):
        vnone = Variable()
        vnone.concretetype = self.TNone
        return SpaceOperation('decref', [v], vnone)
