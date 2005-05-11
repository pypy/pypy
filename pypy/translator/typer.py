from __future__ import generators
import autopath
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.objspace.flow.model import Block, Link, uniqueitems
from pypy.translator.unsimplify import insert_empty_block


class TyperError(Exception):
    pass


class Specializer:

    def __init__(self, annotator, defaultconcretetype, typematches,
                 specializationtable):
        self.annotator = annotator
        self.defaultconcretetype = defaultconcretetype
        self.typematches = typematches
        # turn the table into a dict for faster look-ups
        d = {}
        for e in specializationtable:
            opname1    = e[0]
            opname2    = e[1]
            spectypes  = e[2:-1]
            restype    = e[-1]
            info = opname2, spectypes, restype
            d.setdefault(opname1, []).append(info)
            d.setdefault(opname2, []).append(info)
        self.specializationdict = d

    def specialize(self):
        for block in self.annotator.annotated:
            if block.operations != ():
                self.specialize_block(block)

    def settype(self, a, concretetype):
        """Set the concretetype of a Variable."""
        assert isinstance(a, Variable)
        if hasattr(a, 'concretetype') and a.concretetype != concretetype:
            raise TyperError, "inconsitent type for %r: %r != %r" % (
                a, a.concretetype, concretetype)
        a.concretetype = concretetype

    def setbesttype(self, a):
        """Set the best concretetype for a Variable according to
        the annotations."""
        try:
            return a.concretetype
        except AttributeError:
            s_value = self.annotator.binding(a, True)
            if s_value is not None:
                besttype = self.annotation2concretetype(s_value)
            else:
                besttype = self.defaultconcretetype
            self.settype(a, besttype)
            return besttype

    def annotation2concretetype(self, s_value):
        for concretetype in self.typematches:
            if concretetype.s_annotation.contains(s_value):
                return concretetype
        return self.defaultconcretetype

    def convertvar(self, v, concretetype):
        """Get the operation(s) needed to convert 'v' to the given type."""
        ops = []
        if isinstance(v, Constant):
            # we should never modify a Constant in-place
            v = Constant(v.value)
            v.concretetype = concretetype

        elif v.concretetype != concretetype:
            # XXX do we need better conversion paths?

            # 1) convert to the generic type
            if v.concretetype != self.defaultconcretetype:
                v2 = Variable()
                v2.concretetype = self.defaultconcretetype
                newops = list(v.concretetype.convert_to_obj(self, v, v2))
                v = v2
                ops += newops

            # 2) convert back from the generic type
            if concretetype != self.defaultconcretetype:
                v2 = Variable()
                v2.concretetype = concretetype
                newops = list(concretetype.convert_from_obj(self, v, v2))
                v = v2
                ops += newops

        return v, ops

    def specialize_block(self, block):
        # give the best possible types to the input args
        for a in block.inputargs:
            self.setbesttype(a)

        # specialize all the operations, as far as possible
        newops = []
        for op in block.operations:

            args = list(op.args)
            bindings = [self.annotator.binding(a, True) for a in args]

            # replace constant annotations with real Constants
            for i in range(len(op.args)):
                if isinstance(args[i], Variable) and bindings[i] is not None:
                    if bindings[i].is_constant():
                        args[i] = Constant(bindings[i].const)
                        op = SpaceOperation(op.opname, args, op.result)

            # make a specialized version of the current operation
            # (which may become several operations)
            flatten_ops(self.specialized_op(op, bindings), newops)

        block.operations[:] = newops
        self.insert_link_conversions(block)


    def typed_op(self, op, argtypes, restype, newopname=None):
        """Make a typed copy of the given SpaceOperation."""
        result = []
        args = list(op.args)
        assert len(argtypes) == len(args)

        # type-convert the input arguments
        for i in range(len(args)):
            args[i], convops = self.convertvar(args[i], argtypes[i])
            result += convops

        # store the result variable's type
        self.settype(op.result, restype)

        # store the possibly modified SpaceOperation
        op = SpaceOperation(newopname or op.opname, args, op.result)
        result.append(op)
        return result


    def insert_link_conversions(self, block):
        # insert the needed conversions on the links
        can_insert_here = block.exitswitch is None and len(block.exits) == 1
        for link in block.exits:
            for i in range(len(link.args)):
                a1 = link.args[i]
                if a1 in (link.last_exception, link.last_exc_value):# treated specially in gen_link
                    continue
                a2 = link.target.inputargs[i]
                a2type = self.setbesttype(a2)
                a1, convops = self.convertvar(a1, a2type)
                if convops and not can_insert_here:
                    # cannot insert conversion operations around a single
                    # link, unless it is the only exit of this block.
                    # create a new block along the link...
                    newblock = insert_empty_block(self.annotator.translator,
                                                  link)
                    # ...and do the conversions there.
                    self.insert_link_conversions(newblock)
                    break   # done with this link
                flatten_ops(convops, block.operations)
                link.args[i] = a1


    def specialized_op(self, op, bindings):
        specializations = self.specializationdict.get(op.opname, ())
        for opname2, spectypes, restype in specializations:
            assert len(spectypes) == len(op.args) == len(bindings)
            for i in range(len(spectypes)):
                if bindings[i] is None:
                    break
                if not spectypes[i].s_annotation.contains(bindings[i]):
                    break
            else:
                # specialization found
                yield self.typed_op(op, spectypes, restype, newopname=opname2)
                return
        # specialization not found
        argtypes = [self.defaultconcretetype] * len(op.args)
        yield self.typed_op(op, argtypes, self.defaultconcretetype)


def flatten_ops(op, newops):
    # Flatten lists and generators and record all SpaceOperations found
    if isinstance(op, SpaceOperation):
        newops.append(op)
    else:
        for op1 in op:
            flatten_ops(op1, newops)
