import types
from pypy.rpython.lltypes import *
from pypy.annotation.model import *
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.translator.typer import Specializer, flatten_ops, TyperError
from pypy.rpython.rlist import ListType, substitute_newlist


PyObjPtr = GcPtr(PyObject)

class Retry(Exception):
    """Raised by substitute_*() after they have inserted new patterns
    in the typer's registry.  This asks the typer to try again from
    scratch to specialize the current operation."""


class RPythonTyper(Specializer):
    Retry = Retry

    def __init__(self, annotator):
        # initialization
        Specializer.__init__(self, annotator, defaultconcretetype=PyObjPtr,
                             typematches = [], specializationtable = [],
                             )
        self.registry = {}
        self.typecache = {}
        SINT = SomeInteger()
        self['add', SINT, SINT] = 'int_add', Signed, Signed, Signed
        #self['add', UINT, UINT] = 'int_add', Unsigned, Unsigned, Unsigned

        s_malloc = annotator.bookkeeper.immutablevalue(malloc)
        self['simple_call', s_malloc, ...] = substitute_malloc
        
        # ____________________ lists ____________________
        self['newlist', ...] = substitute_newlist

        # ____________________ conversions ____________________
        self.concreteconversions = {
            (Signed, PyObjPtr): ('int2obj', Signed, PyObjPtr),
            (PyObjPtr, Signed): ('obj2int', PyObjPtr, Signed),
            }

    def __setitem__(self, pattern, substitution):
        patternlist = self.registry.setdefault(pattern[0], [])
        # items inserted last have higher priority
        patternlist.insert(0, (pattern[1:], substitution))

    def maketype(self, cls, s_annotation):
        try:
            return self.typecache[cls, s_annotation]
        except KeyError:
            newtype = cls(s_annotation)
            self.typecache[cls, s_annotation] = newtype
            newtype.define(self)
            return newtype

    def annotation2concretetype(self, s_value):
        try:
            return annotation_to_lltype(s_value)
        except ValueError:
            if isinstance(s_value, SomeList):
                return self.maketype(ListType, s_value).LISTPTR
            return PyObjPtr

    def convertvar(self, v, concretetype):
        """Get the operation(s) needed to convert 'v' to the given type."""
        ops = []
        v_concretetype = getattr(v, 'concretetype', PyObjPtr)
        if isinstance(v, Constant):
            # we should never modify a Constant in-place
            v = Constant(v.value)
            v.concretetype = concretetype

        elif v_concretetype != concretetype:
            try:
                subst = self.concreteconversions[v_concretetype, concretetype]
            except KeyError:
                raise TyperError("cannot convert from %r\n"
                                 "to %r" % (v_concretetype, concretetype))
            vresult = Variable()
            op = SpaceOperation('?', [v], vresult)
            flatten_ops(self.substitute_op(op, subst), ops)
            v = vresult

        return v, ops

    def specialized_op(self, op, bindings):
        assert len(op.args) == len(bindings)

        # first check for direct low-level operations on pointers
        if op.args and isinstance(bindings[0], SomePtr):
            PTR = bindings[0].ll_ptrtype

            if op.opname == 'getitem':
                s_result = self.annotator.binding(op.result)
                T = annotation_to_lltype(s_result, 'getitem')
                return self.typed_op(op, [PTR, Signed], T,
                                     newopname='getarrayitem')

            if op.opname == 'len':
                return self.typed_op(op, [PTR], Signed,
                                     newopname='getarraysize')

            if op.opname == 'getattr':
                assert isinstance(op.args[1], Constant)
                s_result = self.annotator.binding(op.result)
                FIELD_TYPE = PTR.TO._flds[op.args[1].value]
                T = annotation_to_lltype(s_result, 'getattr')
                if isinstance(FIELD_TYPE, ContainerType):
                    newopname = 'getsubstruct'
                else:
                    newopname = 'getfield'
                return self.typed_op(op, [PTR, Void], T, newopname=newopname)

            if op.opname == 'setattr':
                assert isinstance(op.args[1], Constant)
                FIELD_TYPE = PTR.TO._flds[op.args[1].value]
                assert not isinstance(FIELD_TYPE, ContainerType)
                return self.typed_op(op, [PTR, Void, FIELD_TYPE], Void,
                                     newopname='setfield')

            if op.opname == 'eq':
                return self.typed_op(op, [PTR, PTR], Bool,
                                     newopname='ptr_eq')
            if op.opname == 'ne':
                return self.typed_op(op, [PTR, PTR], Bool,
                                     newopname='ptr_ne')

        # generic specialization based on the registration table
        patternlist = self.registry.get(op.opname, [])
        for pattern, substitution in patternlist:
            if pattern and pattern[-1] is Ellipsis:
                pattern = pattern[:-1]
                if len(pattern) > len(op.args):
                    continue
            elif len(pattern) != len(op.args):
                continue
            for s_match, s_value in zip(pattern, bindings):
                if not s_match.contains(s_value):
                    break
            else:
                # match!
                try:
                    return self.substitute_op(op, substitution)
                except Retry:
                    return self.specialized_op(op, bindings)

        # specialization not found
        argtypes = [self.defaultconcretetype] * len(op.args)
        return self.typed_op(op, argtypes, self.defaultconcretetype)

    def substitute_op(self, op, substitution):
        if isinstance(substitution, tuple):
            newopname = substitution[0]
            argtypes = substitution[1:-1]
            resulttype = substitution[-1]
            assert len(argtypes) == len(op.args)
            # None in the substitution list means "remove this argument"
            while None in argtypes:
                argtypes = list(argtypes)
                i = argtypes.index(None)
                del argtypes[i]
                args = list(op.args)
                del args[i]
                op = SpaceOperation(op.opname, args, op.result)
            return self.typed_op(op, argtypes, resulttype,
                                 newopname = newopname)
        else:
            assert callable(substitution), "type error in the registry tables"
            return substitution(self, op)

    def typed_op(self, op, argtypes, restype, newopname=None):
        if isinstance(newopname, types.FunctionType):
            python_function = newopname
            newargs = [Constant(python_function)] + op.args
            op = SpaceOperation('simple_call', newargs, op.result)
            try:
                functyp = python_function.TYPE
            except AttributeError:
                s_returnvalue = self.annotator.build_types(python_function,
                                                           argtypes)
                inferred_type = annotation_to_lltype(s_returnvalue,
                                                     info=python_function)
                if inferred_type != restype:
                    raise TyperError("%r return type mismatch:\n"
                                     "declared %r\n"
                                     "inferred %r" % (python_function,
                                                      inferred_type, restype))
                functyp = NonGcPtr(FuncType(argtypes, restype))
                python_function.TYPE = functyp
            argtypes = [functyp] + list(argtypes)
            newopname = None
        return Specializer.typed_op(self, op, argtypes, restype, newopname)


def substitute_malloc(typer, op):
    s_result = typer.annotator.binding(op.result)
    T = annotation_to_lltype(s_result, 'malloc')
    if len(op.args) == 2:
        substitution = 'malloc', None, Void, T
    else:
        substitution = 'malloc_varsize', None, Void, Signed, T
    return typer.substitute_op(op, substitution)
