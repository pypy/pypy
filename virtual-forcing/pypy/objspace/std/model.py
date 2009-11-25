"""
The full list of which Python types and which implementation we want
to provide in this version of PyPy, along with conversion rules.
"""

from pypy.objspace.std.multimethod import MultiMethodTable, FailedToImplement
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
import pypy.interpreter.pycode
import pypy.interpreter.special

option_to_typename = {
    "withsmallint"   : ["smallintobject.W_SmallIntObject"],
    "withstrslice"   : ["strsliceobject.W_StringSliceObject"],
    "withstrjoin"    : ["strjoinobject.W_StringJoinObject"],
    "withrope"       : ["ropeobject.W_RopeObject",
                        "ropeobject.W_RopeIterObject"],
    "withropeunicode": ["ropeunicodeobject.W_RopeUnicodeObject",
                        "ropeunicodeobject.W_RopeUnicodeIterObject"],
    "withrangelist"  : ["rangeobject.W_RangeListObject",
                        "rangeobject.W_RangeIterObject"],
    "withtproxy" : ["proxyobject.W_TransparentList",
                    "proxyobject.W_TransparentDict"],
}

class StdTypeModel:

    def __init__(self, config):
        """NOT_RPYTHON: inititialization only"""
        self.config = config
        # All the Python types that we want to provide in this StdObjSpace
        class result:
            from pypy.objspace.std.objecttype import object_typedef
            from pypy.objspace.std.booltype   import bool_typedef
            from pypy.objspace.std.inttype    import int_typedef
            from pypy.objspace.std.floattype  import float_typedef
            from pypy.objspace.std.complextype  import complex_typedef
            from pypy.objspace.std.settype import set_typedef
            from pypy.objspace.std.frozensettype import frozenset_typedef
            from pypy.objspace.std.tupletype  import tuple_typedef
            from pypy.objspace.std.listtype   import list_typedef
            from pypy.objspace.std.dicttype   import dict_typedef
            from pypy.objspace.std.basestringtype import basestring_typedef
            from pypy.objspace.std.stringtype import str_typedef
            from pypy.objspace.std.typetype   import type_typedef
            from pypy.objspace.std.slicetype  import slice_typedef
            from pypy.objspace.std.longtype   import long_typedef
            from pypy.objspace.std.unicodetype import unicode_typedef
            from pypy.objspace.std.dictproxytype import dictproxy_typedef
            from pypy.objspace.std.nonetype import none_typedef
            from pypy.objspace.std.itertype import iter_typedef
        self.pythontypes = [value for key, value in result.__dict__.items()
                            if not key.startswith('_')]   # don't look

        # The object implementations that we want to 'link' into PyPy must be
        # imported here.  This registers them into the multimethod tables,
        # *before* the type objects are built from these multimethod tables.
        from pypy.objspace.std import objectobject
        from pypy.objspace.std import boolobject
        from pypy.objspace.std import intobject
        from pypy.objspace.std import floatobject
        from pypy.objspace.std import complexobject
        from pypy.objspace.std import setobject
        from pypy.objspace.std import smallintobject
        from pypy.objspace.std import tupleobject
        from pypy.objspace.std import listobject
        from pypy.objspace.std import dictmultiobject
        from pypy.objspace.std import stringobject
        from pypy.objspace.std import ropeobject
        from pypy.objspace.std import ropeunicodeobject
        from pypy.objspace.std import strsliceobject
        from pypy.objspace.std import strjoinobject
        from pypy.objspace.std import typeobject
        from pypy.objspace.std import sliceobject
        from pypy.objspace.std import longobject
        from pypy.objspace.std import noneobject
        from pypy.objspace.std import iterobject
        from pypy.objspace.std import unicodeobject
        from pypy.objspace.std import dictproxyobject
        from pypy.objspace.std import rangeobject
        from pypy.objspace.std import proxyobject
        from pypy.objspace.std import fake
        import pypy.objspace.std.default # register a few catch-all multimethods

        import pypy.objspace.std.marshal_impl # install marshal multimethods

        # the set of implementation types
        self.typeorder = {
            objectobject.W_ObjectObject: [],
            boolobject.W_BoolObject: [],
            intobject.W_IntObject: [],
            floatobject.W_FloatObject: [],
            tupleobject.W_TupleObject: [],
            listobject.W_ListObject: [],
            dictmultiobject.W_DictMultiObject: [],
            dictmultiobject.W_DictMultiIterObject: [],
            stringobject.W_StringObject: [],
            typeobject.W_TypeObject: [],
            sliceobject.W_SliceObject: [],
            longobject.W_LongObject: [],
            noneobject.W_NoneObject: [],
            complexobject.W_ComplexObject: [],
            setobject.W_BaseSetObject: [],
            setobject.W_SetObject: [],
            setobject.W_FrozensetObject: [],
            setobject.W_SetIterObject: [],
            iterobject.W_SeqIterObject: [],
            iterobject.W_FastListIterObject: [],
            iterobject.W_FastTupleIterObject: [],
            iterobject.W_ReverseSeqIterObject: [],
            unicodeobject.W_UnicodeObject: [],
            dictproxyobject.W_DictProxyObject: [],
            pypy.interpreter.pycode.PyCode: [],
            pypy.interpreter.special.Ellipsis: [],
            }

        self.imported_but_not_registered = {
            dictmultiobject.W_DictMultiObject: True, # XXXXXX
            dictmultiobject.W_DictMultiIterObject: True,
            listobject.W_ListObject: True,
            stringobject.W_StringObject: True,
            tupleobject.W_TupleObject: True,
        }
        for option, value in config.objspace.std:
            if option.startswith("with") and option in option_to_typename:
                for classname in option_to_typename[option]:
                    implcls = eval(classname)
                    if value:
                        self.typeorder[implcls] = []
                    else:
                        self.imported_but_not_registered[implcls] = True

        if config.objspace.std.withrope:
            del self.typeorder[stringobject.W_StringObject]

        #check if we missed implementations
        from pypy.objspace.std.objspace import _registered_implementations
        for implcls in _registered_implementations:
            assert (implcls in self.typeorder or
                    implcls in self.imported_but_not_registered), (
                "please add %r in StdTypeModel.typeorder" % (implcls,))


        for type in self.typeorder:
            self.typeorder[type].append((type, None))

        # register the order in which types are converted into each others
        # when trying to dispatch multimethods.
        # XXX build these lists a bit more automatically later
        
        if config.objspace.std.withsmallint:
            self.typeorder[boolobject.W_BoolObject] += [
                (smallintobject.W_SmallIntObject, boolobject.delegate_Bool2SmallInt),
                ]
            self.typeorder[smallintobject.W_SmallIntObject] += [
                (intobject.W_IntObject, smallintobject.delegate_SmallInt2Int),
                (floatobject.W_FloatObject, smallintobject.delegate_SmallInt2Float),
                (longobject.W_LongObject, smallintobject.delegate_SmallInt2Long),
                (complexobject.W_ComplexObject, smallintobject.delegate_SmallInt2Complex),
                ]

        self.typeorder[boolobject.W_BoolObject] += [
            (intobject.W_IntObject,     boolobject.delegate_Bool2IntObject),
            (floatobject.W_FloatObject, floatobject.delegate_Bool2Float),
            (longobject.W_LongObject,   longobject.delegate_Bool2Long),
            (complexobject.W_ComplexObject, complexobject.delegate_Bool2Complex),
            ]
        self.typeorder[intobject.W_IntObject] += [
            (floatobject.W_FloatObject, floatobject.delegate_Int2Float),
            (longobject.W_LongObject,   longobject.delegate_Int2Long),
            (complexobject.W_ComplexObject, complexobject.delegate_Int2Complex),
            ]
        self.typeorder[longobject.W_LongObject] += [
            (floatobject.W_FloatObject, floatobject.delegate_Long2Float),
            (complexobject.W_ComplexObject, 
                    complexobject.delegate_Long2Complex),
            ]
        self.typeorder[floatobject.W_FloatObject] += [
            (complexobject.W_ComplexObject, 
                    complexobject.delegate_Float2Complex),
            ]
        self.typeorder[setobject.W_SetObject] += [
            (setobject.W_BaseSetObject, None)
            ]
        self.typeorder[setobject.W_FrozensetObject] += [
            (setobject.W_BaseSetObject, None)
            ]
        if not config.objspace.std.withrope:
            self.typeorder[stringobject.W_StringObject] += [
             (unicodeobject.W_UnicodeObject, unicodeobject.delegate_String2Unicode),
                ]
        else:
            if config.objspace.std.withropeunicode:
                self.typeorder[ropeobject.W_RopeObject] += [
                 (ropeunicodeobject.W_RopeUnicodeObject,
                     ropeunicodeobject.delegate_Rope2RopeUnicode),
                 ]
            else:
                self.typeorder[ropeobject.W_RopeObject] += [
                 (unicodeobject.W_UnicodeObject, unicodeobject.delegate_String2Unicode),
                    ]

        if config.objspace.std.withstrslice:
            self.typeorder[strsliceobject.W_StringSliceObject] += [
                (stringobject.W_StringObject,
                                       strsliceobject.delegate_slice2str),
                (unicodeobject.W_UnicodeObject,
                                       strsliceobject.delegate_slice2unicode),
                ]
        if config.objspace.std.withstrjoin:
            self.typeorder[strjoinobject.W_StringJoinObject] += [
                (stringobject.W_StringObject,
                                       strjoinobject.delegate_join2str),
                (unicodeobject.W_UnicodeObject,
                                       strjoinobject.delegate_join2unicode)
                ]
        if config.objspace.std.withrangelist:
            self.typeorder[rangeobject.W_RangeListObject] += [
                (listobject.W_ListObject,
                                       rangeobject.delegate_range2list),
                ]

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

# ____________________________________________________________

W_ANY = W_Root

class W_Object(W_Root):
    "Parent base class for wrapped objects provided by the StdObjSpace."
    # Note that not all wrapped objects in the interpreter inherit from
    # W_Object.  (They inherit from W_Root.)
    __slots__ = ()

    def __repr__(self):
        s = '%s(%s)' % (
            self.__class__.__name__,
           #', '.join(['%s=%r' % keyvalue for keyvalue in self.__dict__.items()])
            getattr(self, 'name', '')
            )
        w_cls = getattr(self, 'w__class__', None)
        if w_cls is not None and w_cls is not self:
            s += ' instance of %s' % self.w__class__
        return '<%s>' % s

    def unwrap(w_self, space):
        raise UnwrapError, 'cannot unwrap %r' % (w_self,)

class UnwrapError(Exception):
    pass


class StdObjSpaceMultiMethod(MultiMethodTable):

    def __init__(self, operatorsymbol, arity, specialnames=None, **extras):
        """NOT_RPYTHON: cannot create new multimethods dynamically.
        """
        MultiMethodTable.__init__(self, arity, W_ANY,
                                  argnames_before = ['space'])
        self.operatorsymbol = operatorsymbol
        if specialnames is None:
            specialnames = [operatorsymbol]
        self.specialnames = specialnames  # e.g. ['__xxx__', '__rxxx__']
        self.extras = extras
        # transform  '+'  =>  'add'  etc.
        for line in ObjSpace.MethodTable:
            realname, symbolname = line[:2]
            if symbolname == operatorsymbol:
                self.name = realname
                break
        else:
            self.name = operatorsymbol
            
        if extras.get('general__args__', False):
            self.argnames_after = ['__args__']
        if extras.get('w_varargs', False):
            self.argnames_after = ['w_args']
        if extras.get('varargs_w', False):
            self.argnames_after = ['args_w']            
        self.argnames_after += extras.get('extra_args', [])

    def install_not_sliced(self, typeorder, baked_perform_call=True):
        return self.install(prefix = '__mm_' + self.name,
                list_of_typeorders = [typeorder]*self.arity,
                baked_perform_call=baked_perform_call)

    def merge_with(self, other):
        # Make a new 'merged' multimethod including the union of the two
        # tables.  In case of conflict, pick the entry from 'self'.
        if self.arity != other.arity:
            return self      # XXX that's the case of '**'
        operatorsymbol = '%s_merge_%s' % (self.name, other.name)
        assert self.extras == other.extras
        mm = StdObjSpaceMultiMethod(operatorsymbol, self.arity, **self.extras)
        #
        def merge(node1, node2):
            assert type(node1) is type(node2)
            if isinstance(node1, dict):
                d = node1.copy()
                d.update(node2)
                for key in node1:
                    if key in node2:
                        d[key] = merge(node1[key], node2[key])
                return d
            else:
                assert isinstance(node1, list)
                assert node1
                return node1     # pick the entry from 'self'
        #
        mm.dispatch_tree = merge(self.dispatch_tree, other.dispatch_tree)
        return mm
