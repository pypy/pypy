"""
The full list of which Python types and which implementation we want
to provide in this version of PyPy, along with conversion rules.
"""

from pypy.interpreter.baseobjspace import W_Root, ObjSpace
import pypy.interpreter.pycode
import pypy.interpreter.special

_registered_implementations = set()
def registerimplementation(implcls):
    """Hint to objspace.std.model to register the implementation class."""
    assert issubclass(implcls, W_Object)
    _registered_implementations.add(implcls)

option_to_typename = {
    "withsmalllong"  : ["smalllongobject.W_SmallLongObject"],
    "withstrbuf"     : ["strbufobject.W_StringBufferObject"],
}

IDTAG_INT     = 1
IDTAG_LONG    = 3
IDTAG_FLOAT   = 5
IDTAG_COMPLEX = 7

class StdTypeModel:

    def __init__(self, config):
        """NOT_RPYTHON: inititialization only"""
        self.config = config
        # All the Python types that we want to provide in this StdObjSpace

        # The object implementations that we want to 'link' into PyPy must be
        # imported here.  This registers them into the multimethod tables,
        # *before* the type objects are built from these multimethod tables.
        from pypy.objspace.std import objectobject
        from pypy.objspace.std import boolobject
        from pypy.objspace.std import intobject
        from pypy.objspace.std import floatobject
        from pypy.objspace.std import complexobject
        from pypy.objspace.std import tupleobject
        from pypy.objspace.std import listobject
        from pypy.objspace.std import dictmultiobject
        from pypy.objspace.std import setobject
        from pypy.objspace.std import basestringtype
        from pypy.objspace.std import bytesobject
        from pypy.objspace.std import bytearrayobject
        from pypy.objspace.std import typeobject
        from pypy.objspace.std import sliceobject
        from pypy.objspace.std import longobject
        from pypy.objspace.std import noneobject
        from pypy.objspace.std import iterobject
        from pypy.objspace.std import unicodeobject
        from pypy.objspace.std import dictproxyobject
        from pypy.objspace.std import proxyobject


        self.pythontypes = []
        self.pythontypes.append(objectobject.W_ObjectObject.typedef)
        self.pythontypes.append(typeobject.W_TypeObject.typedef)
        self.pythontypes.append(noneobject.W_NoneObject.typedef)
        self.pythontypes.append(tupleobject.W_TupleObject.typedef)
        self.pythontypes.append(listobject.W_ListObject.typedef)
        self.pythontypes.append(dictmultiobject.W_DictMultiObject.typedef)
        self.pythontypes.append(setobject.W_SetObject.typedef)
        self.pythontypes.append(setobject.W_FrozensetObject.typedef)
        self.pythontypes.append(iterobject.W_AbstractSeqIterObject.typedef)
        self.pythontypes.append(basestringtype.basestring_typedef)
        self.pythontypes.append(bytesobject.W_BytesObject.typedef)
        self.pythontypes.append(bytearrayobject.W_BytearrayObject.typedef)
        self.pythontypes.append(unicodeobject.W_UnicodeObject.typedef)
        self.pythontypes.append(intobject.W_IntObject.typedef)
        self.pythontypes.append(boolobject.W_BoolObject.typedef)
        self.pythontypes.append(longobject.W_LongObject.typedef)
        self.pythontypes.append(floatobject.W_FloatObject.typedef)
        self.pythontypes.append(complexobject.W_ComplexObject.typedef)
        self.pythontypes.append(sliceobject.W_SliceObject.typedef)

        # the set of implementation types
        self.typeorder = {
            objectobject.W_ObjectObject: [],
            # XXX: Bool/Int/Long are pythontypes but still included here
            # for delegation to Float/Complex
            boolobject.W_BoolObject: [],
            intobject.W_IntObject: [],
            floatobject.W_FloatObject: [],
            typeobject.W_TypeObject: [],
            sliceobject.W_SliceObject: [],
            longobject.W_LongObject: [],
            noneobject.W_NoneObject: [],
            complexobject.W_ComplexObject: [],
            pypy.interpreter.pycode.PyCode: [],
            pypy.interpreter.special.Ellipsis: [],
            }

        self.imported_but_not_registered = {
            bytesobject.W_BytesObject: True,
        }
        for option, value in config.objspace.std:
            if option.startswith("with") and option in option_to_typename:
                for classname in option_to_typename[option]:
                    modname = classname[:classname.index('.')]
                    classname = classname[classname.index('.')+1:]
                    d = {}
                    exec "from pypy.objspace.std.%s import %s" % (
                        modname, classname) in d
                    implcls = d[classname]
                    if value:
                        self.typeorder[implcls] = []
                    else:
                        self.imported_but_not_registered[implcls] = True

        # check if we missed implementations
        for implcls in _registered_implementations:
            if hasattr(implcls, 'register'):
                implcls.register(self.typeorder)
            assert (implcls in self.typeorder or
                    implcls in self.imported_but_not_registered), (
                "please add %r in StdTypeModel.typeorder" % (implcls,))


        for type in self.typeorder:
            self.typeorder[type].append((type, None))

        # register the order in which types are converted into each others
        # when trying to dispatch multimethods.
        # XXX build these lists a bit more automatically later

        if config.objspace.std.withsmalllong:
            from pypy.objspace.std import smalllongobject
            self.typeorder[smalllongobject.W_SmallLongObject] += [
                (floatobject.W_FloatObject, smalllongobject.delegate_SmallLong2Float),
                (complexobject.W_ComplexObject, smalllongobject.delegate_SmallLong2Complex),
                ]

        if config.objspace.std.withstrbuf:
            from pypy.objspace.std import strbufobject

        # put W_Root everywhere
        self.typeorder[W_Root] = []
        for type in self.typeorder:
            from pypy.objspace.std import stdtypedef
            if type is not W_Root and isinstance(type.typedef, stdtypedef.StdTypeDef):
                self.typeorder[type].append((type.typedef.any, None))
            self.typeorder[type].append((W_Root, None))

        self._typeorder_with_empty_usersubcls = None

        # ____________________________________________________________
        # Prebuilt common integer values

        if config.objspace.std.withprebuiltint:
            intobject.W_IntObject.PREBUILT = []
            for i in range(config.objspace.std.prebuiltintfrom,
                           config.objspace.std.prebuiltintto):
                intobject.W_IntObject.PREBUILT.append(intobject.W_IntObject(i))
            del i
        else:
            intobject.W_IntObject.PREBUILT = None

        # ____________________________________________________________

    def get_typeorder_with_empty_usersubcls(self):
        if self._typeorder_with_empty_usersubcls is None:
            from pypy.interpreter.typedef import enum_interplevel_subclasses
            from pypy.objspace.std import stdtypedef
            result = self.typeorder.copy()
            for cls in self.typeorder:
                if (hasattr(cls, 'typedef') and cls.typedef is not None and
                    cls.typedef.acceptable_as_base_class):
                    subclslist = enum_interplevel_subclasses(self.config, cls)
                    for subcls in subclslist:
                        if cls in subcls.__bases__:   # only direct subclasses
                            # for user subclasses we only accept "generic"
                            # matches: "typedef.any" is the applevel-type-based
                            # matching, and "W_Root" is ANY.
                            matches = []
                            if isinstance(cls.typedef, stdtypedef.StdTypeDef):
                                matches.append((cls.typedef.any, None))
                            matches.append((W_Root, None))
                            result[subcls] = matches
            self._typeorder_with_empty_usersubcls = result
        return self._typeorder_with_empty_usersubcls

def _op_negated(function):
    def op(space, w_1, w_2):
        return space.not_(function(space, w_1, w_2))
    return op

def _op_swapped(function):
    def op(space, w_1, w_2):
        return function(space, w_2, w_1)
    return op

def _op_swapped_negated(function):
    def op(space, w_1, w_2):
        return space.not_(function(space, w_2, w_1))
    return op


CMP_OPS = dict(lt='<', le='<=', eq='==', ne='!=', gt='>', ge='>=')
CMP_CORRESPONDANCES = [
    ('eq', 'ne', _op_negated),
    ('lt', 'gt', _op_swapped),
    ('le', 'ge', _op_swapped),
    ('lt', 'ge', _op_negated),
    ('le', 'gt', _op_negated),
    ('lt', 'le', _op_swapped_negated),
    ('gt', 'ge', _op_swapped_negated),
    ]
for op1, op2, value in CMP_CORRESPONDANCES[:]:
    i = CMP_CORRESPONDANCES.index((op1, op2, value))
    CMP_CORRESPONDANCES.insert(i+1, (op2, op1, value))
BINARY_BITWISE_OPS = {'and': '&', 'lshift': '<<', 'or': '|', 'rshift': '>>',
                      'xor': '^'}
BINARY_OPS = dict(add='+', div='/', floordiv='//', mod='%', mul='*', sub='-',
                  truediv='/', **BINARY_BITWISE_OPS)
COMMUTATIVE_OPS = ('add', 'mul', 'and', 'or', 'xor')

def add_extra_comparisons():
    """
    Add the missing comparison operators if they were not explicitly
    defined:  eq <-> ne  and  lt <-> le <-> gt <-> ge.
    We try to add them in the order defined by the CMP_CORRESPONDANCES
    table, thus favouring swapping the arguments over negating the result.
    """
    originalentries = {}
    for op in CMP_OPS.iterkeys():
        originalentries[op] = getattr(MM, op).signatures()

    for op1, op2, correspondance in CMP_CORRESPONDANCES:
        mirrorfunc = getattr(MM, op2)
        for types in originalentries[op1]:
            t1, t2 = types
            if t1 is t2:
                if not mirrorfunc.has_signature(types):
                    functions = getattr(MM, op1).getfunctions(types)
                    assert len(functions) == 1, ('Automatic'
                            ' registration of comparison functions'
                            ' only work when there is a single method for'
                            ' the operation.')
                    mirrorfunc.register(correspondance(functions[0]), *types)


# ____________________________________________________________

W_ANY = W_Root

class W_Object(W_Root):
    "Parent base class for wrapped objects provided by the StdObjSpace."
    # Note that not all wrapped objects in the interpreter inherit from
    # W_Object.  (They inherit from W_Root.)
    __slots__ = ()

    def __repr__(self):
        name = getattr(self, 'name', '')
        if not isinstance(name, str):
            name = ''
        s = '%s(%s)' % (self.__class__.__name__, name)
        w_cls = getattr(self, 'w__class__', None)
        if w_cls is not None and w_cls is not self:
            s += ' instance of %s' % self.w__class__
        return '<%s>' % s


class UnwrapError(Exception):
    pass
