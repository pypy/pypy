import autopath
from pypy.annotation.model import *
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.translator.transform import fully_annotated_blocks


S_INT = SomeInteger()

SpecializationTable = [
    ('add',     'int_add',     S_INT, S_INT),
    ('sub',     'int_sub',     S_INT, S_INT),
    ('is_true', 'int_is_true', S_INT),
    ]

TypesToConvert = {
    SomeInteger: ('int2obj', 'obj2int'),
    }

def setup_specialization_dict():
    for e in SpecializationTable:
        spectypes = e[2:]
        opname1   = e[0]
        opname2   = e[1]
        SpecializationDict.setdefault(opname1, []).append((opname2, spectypes))
        SpecializationDict.setdefault(opname2, []).append((opname2, spectypes))

SpecializationDict = {}
setup_specialization_dict()

# ____________________________________________________________

def specialize(annotator):
    for block in fully_annotated_blocks(annotator):
        if not block.operations:
            continue
        newops = []
        for op in block.operations:

            indices = range(len(op.args))
            args = list(op.args)
            bindings = [annotator.binding(a, True) for a in args]
            noteworthyindices = []

            for i in indices:
                if isinstance(args[i], Variable) and bindings[i] is not None:
                    if bindings[i].is_constant():
                        args[i] = Constant(bindings[i].const)
                    else:
                        noteworthyindices.append(i)

            specializations = SpecializationDict.get(op.opname, ())
            for opname2, spectypes in specializations:
                assert len(spectypes) == len(op.args)
                for i in indices:
                    if bindings[i] is None:
                        break
                    if not spectypes[i].contains(bindings[i]):
                        break
                else:
                    op = SpaceOperation(opname2, args, op.result)
                    break
            else:
                for i in noteworthyindices:
                    for cls in bindings[i].__class__.__mro__:
                        if cls in TypesToConvert:
                            convert, backconvert = TypesToConvert[cls]
                            result = Variable()
                            newops.append(SpaceOperation(convert, [args[i]],
                                                         result))
                            args[i] = result
                            break
                if args != op.args:
                    op = SpaceOperation(op.opname, args, op.result)
                result = op.result
                result_binding = annotator.binding(result, True)
                if result_binding is not None:
                    for cls in result_binding.__class__.__mro__:
                        if cls in TypesToConvert:
                            convert, backconvert = TypesToConvert[cls]
                            intermediate = Variable()
                            newops.append(SpaceOperation(op.opname, args,
                                                         intermediate))
                            op = SpaceOperation(backconvert, [intermediate],
                                                result)
                            break

            newops.append(op)
        block.operations[:] = newops
