import autopath
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.objspace.flow.model import Block, Link, uniqueitems


class TypeMatch:
    def __init__(self, s_type, type_cls):
        self.s_type = s_type
        self.type_cls = type_cls

class TyperError:
    pass


class Specializer:
    specializationdict = {}

    def __init__(self, annotator):
        if not self.specializationdict:
            # setup the class
            d = self.specializationdict
            for e in self.specializationtable:
                opname1    = e[0]
                opname2    = e[1]
                spectypes  = e[2:-1]
                restypecls = e[-1]
                info = opname2, spectypes, restypecls
                d.setdefault(opname1, []).append(info)
                d.setdefault(opname2, []).append(info)
        self.annotator = annotator

    def specialize(self):
        for block in self.annotator.annotated:
            if block.operations != ():
                self.specialize_block(block)

    def settype(self, a, type_cls):
        """Set the type_cls of a Variable or Constant."""
        if hasattr(a, 'type_cls') and a.type_cls != type_cls:
            raise TyperError, "inconsitent type for %r" % (a,)
        a.type_cls = type_cls

    def setbesttype(self, a):
        """Set the best type_cls for a Variable or Constant according to
        the annotations."""
        try:
            return a.type_cls
        except AttributeError:
            besttype = self.defaulttypecls
            s_value = self.annotator.binding(a, True)
            if s_value is not None:
                for tmatch in self.typematches:
                    if tmatch.s_type.contains(s_value):
                        besttype = tmatch.type_cls
                        break
            self.settype(a, besttype)
            return besttype

    def convertvar(self, v, type_cls):
        """Get the operation(s) needed to convert 'v' to the given type."""
        ops = []
        if isinstance(v, Constant):
            try:
                # mark the concrete type of the Constant
                self.settype(v, type_cls)
            except TyperError:
                v = Constant(v.value)   # need a copy of the Constant
                self.settype(v, type_cls)

        elif v.type_cls is not type_cls:
            # XXX do we need better conversion paths?

            # 1) convert to the generic type
            if v.type_cls is not self.defaulttypecls:
                v2 = Variable()
                v2.type_cls = self.defaulttypecls
                op = SpaceOperation(v.type_cls.convert_to_obj, [v], v2)
                v = v2
                ops.append(op)

            # 2) convert back from the generic type
            if type_cls is not self.defaulttypecls:
                v2 = Variable()
                v2.type_cls = type_cls
                op = SpaceOperation(type_cls.convert_from_obj, [v], v2)
                v = v2
                ops.append(op)

        return v, ops

    def specialize_block(self, block):
        # give the best possible types to the input args
        for a in block.inputargs:
            self.setbesttype(a)

        # specialize all the operations, as far as possible
        newops = []
        for op in block.operations:

            indices = range(len(op.args))
            args = list(op.args)
            bindings = [self.annotator.binding(a, True) for a in args]

            # replace constant annotations with real Constants
            for i in indices:
                if isinstance(args[i], Variable) and bindings[i] is not None:
                    if bindings[i].is_constant():
                        args[i] = Constant(bindings[i].const)

            # look for a specialized version of the current operation
            opname2, argtypes, restypecls = self.getspecializedop(op, bindings)

            # type-convert the input arguments
            for i in indices:
                args[i], convops = self.convertvar(args[i], argtypes[i])
                newops += convops

            # store the result variable's type
            self.settype(op.result, restypecls)

            # store the possibly modified SpaceOperation
            if opname2 != op.opname or args != op.args:
                op = SpaceOperation(opname2, args, op.result)
            newops.append(op)

        block.operations[:] = newops

        # insert the needed conversions on the links
        for link in block.exits:
            # numbering of Variables:
            #    a1 in the original Link
            #    a2 in the inserted block before conversion
            #    a3 in the inserted block after conversion
            #    a4 in the original target block's inputargs
            # warning, link.args may contain the same Variable multiple times!
            convargs = []
            convops = []
            for i in range(len(link.args)):
                a1 = link.args[i]
                a4 = link.target.inputargs[i]
                a4type = self.setbesttype(a4)
                a3, convop1 = self.convertvar(a1, a4type)
                convargs.append(a3)
                convops += convop1
            # if there are conversion operations, they are inserted into
            # a new block along this link
            if convops:
                vars = uniqueitems([a1 for a1 in link.args
                                       if isinstance(a1, Variable)])
                newblock = Block([])
                mapping = {}
                for a1 in vars:
                    a2 = Variable()
                    a2.type_cls = a1.type_cls
                    newblock.inputargs.append(a2)
                    mapping[a1] = a2
                newblock.operations = convops
                newblock.closeblock(Link(convargs, link.target))
                newblock.renamevariables(mapping)
                link.target = newblock
                link.args[:] = vars
            else:
                link.args[:] = convargs   # some Constants may have changed

    def getspecializedop(self, op, bindings):
        specializations = self.specializationdict.get(op.opname, ())
        for opname2, spectypes, restypecls in specializations:
            assert len(spectypes) == len(op.args) == len(bindings)
            for i in range(len(spectypes)):
                if bindings[i] is None:
                    break
                if not spectypes[i].s_type.contains(bindings[i]):
                    break
            else:
                # specialization found
                # opname2 and restypecls are set above by the for loop
                argtypes = [tmatch.type_cls for tmatch in spectypes]
                break
        else:
            # specialization not found
            opname2 = op.opname
            argtypes = [CType_PyObject] * len(op.args)
            restypecls = self.defaulttypecls
        return opname2, argtypes, restypecls

# ____________________________________________________________
# GenC-specific specializer

from pypy.annotation.model import SomeInteger
from pypy.translator.genc_pyobj import CType_PyObject
from pypy.translator.genc_type import CType_Int

class GenCSpecializer(Specializer):

    TInt = TypeMatch(SomeInteger(), CType_Int)
    typematches = [TInt]   # in more-specific-first, more-general-last order
    defaulttypecls = CType_PyObject

    specializationtable = [
        ## op      specialized op   arg types   concrete return type
        ('add',     'int_add',     TInt, TInt,   CType_Int),
        ('sub',     'int_sub',     TInt, TInt,   CType_Int),
        ('is_true', 'int_is_true', TInt,         CType_Int),
        ]
