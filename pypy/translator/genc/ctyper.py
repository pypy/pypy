"""
GenC-specific type specializer
"""

from __future__ import generators
from pypy.translator.typer import Specializer
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.annotation.model import SomeInteger, SomePBC, SomeTuple
from pypy.translator.genc.t_pyobj import CPyObjectType
from pypy.translator.genc.t_simple import CIntType, CNoneType
from pypy.translator.genc.t_func import CFuncPtrType
import types
from pypy.interpreter.pycode import CO_VARARGS

class GenCSpecializer(Specializer):

    def __init__(self, annotator):
        # instantiate the common concrete types
        t = annotator.translator
        TInt      = t.getconcretetype(CIntType)
        TNone     = t.getconcretetype(CNoneType)
        TPyObject = t.getconcretetype(CPyObjectType)

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

##            elif isinstance(s_value, SomeTuple):
##                key = tuple([self.annotation2concretetype(s_item)
##                             for s_item in s_value.items])
##                besttype = CType_Tuple[key]

        return besttype

    def make_specialized_op(self, op, bindings):
        if op.opname == 'simple_call':
            s_callable = self.annotator.binding(op.args[0], True)
            if s_callable is not None:
                ct = self.annotation2concretetype(s_callable)
                if isinstance(ct, CFuncPtrType):
                    argtypes = [ct]
                    argtypes += ct.argtypes
                    self.make_typed_op(op, argtypes, ct.returntype,
                                       newopname='direct_call')
                    return

##        if op.opname == 'getitem':
##            s_obj = self.annotator.binding(op.args[0], True)
##            if s_obj is not None:
##                ct = self.annotation2typecls(s_obj)
##                if issubclass(ct, CType_Tuple):
##                    if isinstance(op.args[1], Constant):
##                        index = op.args[1].value
##                        try:
##                            ct1 = ct.items_typecls[index]
##                        except IndexError:
##                            print "*** getitem: IndexError in tuple access"
##                        else:
##                            self.make_typed_op(op, [ct, CType_Int], ct1,
##                                               newopname='tuple_getitem')
##                            return

##        if op.opname == 'newtuple':
##            s_tuple = self.annotator.binding(op.result, True)
##            if s_tuple is not None:
##                ct = self.annotation2typecls(s_tuple)
##                if issubclass(ct, CType_Tuple):
##                    op1 = SpaceOperation('tuple_new', [], op.result)
##                    self.make_typed_op(op1, [], ct)
##                    for i in range(len(ct.items_typecls)):
##                        op1 = SpaceOperation('tuple_inititem',
##                                         [op.result, Constant(i), op.args[i]],
##                                         Variable())
##                        ct1 = ct.items_typecls[i]
##                        self.make_typed_op(op1,
##                                           [ct, CType_Int, ct1],
##                                           CType_None)
##                    return

        Specializer.make_specialized_op(self, op, bindings)
