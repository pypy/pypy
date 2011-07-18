import py
from py.builtin import set
from pypy.rpython.lltypesystem.lltype import LowLevelType, Signed, Unsigned, Float, Char
from pypy.rpython.lltypesystem.lltype import Bool, Void, UniChar, typeOf, \
        Primitive, isCompatibleType, enforce, saferecursive, SignedLongLong, UnsignedLongLong
from pypy.rpython.lltypesystem.lltype import frozendict
from pypy.rpython.lltypesystem.lltype import identityhash
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import objectmodel
from pypy.tool.uid import uid


STATICNESS = True

class OOType(LowLevelType):

    oopspec_name = None

    _classes = {}

    @property
    def _class(self):
        try:
            return self._classes[self]
        except KeyError:
            cls = _class(self)
            self._classes[self] = cls
            return cls


    def _is_compatible(TYPE1, TYPE2):
        if TYPE1 == TYPE2:
            return True
        if isinstance(TYPE1, Instance) and isinstance(TYPE2, Instance):
            return isSubclass(TYPE1, TYPE2)
        else:
            return False

    def _enforce(TYPE2, value):
        TYPE1 = typeOf(value)
        if TYPE1 == TYPE2:
            return value
        if isinstance(TYPE1, Instance) and isinstance(TYPE2, Instance):
            if isSubclass(TYPE1, TYPE2):
                return value._enforce(TYPE2)
        raise TypeError


class ForwardReference(OOType):
    def become(self, realtype):
        if not isinstance(realtype, OOType):
            raise TypeError("ForwardReference can only be to an OOType, "
                            "not %r" % (realtype,))
        self.__class__ = realtype.__class__
        self.__dict__ = realtype.__dict__

    def __hash__(self):
        raise TypeError("%r object is not hashable" % self.__class__.__name__)


# warning: the name Object is rebount at the end of file
class Object(OOType):
    """
    A type which everything can be casted to.
    """

    def _defl(self):
        return self._null


class Class(OOType):

    def _defl(self):
        return nullruntimeclass

    def _example(self):
        return _class(ROOT)
    
Class = Class()

class Instance(OOType):
    """this is the type of user-defined objects"""
    def __init__(self, name, superclass, fields={}, methods={},
            _is_root=False, _hints = {}):
        self._name = name
        self._hints = frozendict(_hints)
        self._subclasses = []

        if _is_root:
            self._superclass = None
        else:
            if superclass is not None:
                self._set_superclass(superclass)

        self._methods = frozendict()
        self._fields = frozendict()
        self._overridden_defaults = frozendict()
        self._fields_with_default = []

        self._add_fields(fields)
        self._add_methods(methods)

        self._null = make_null_instance(self)
        self.__dict__['_class'] = _class(self)

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __hash__(self):
        return object.__hash__(self)
        
    def _defl(self):
        return self._null

    def _example(self): return new(self)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._name)

    def _set_superclass(self, superclass):
        assert isinstance(superclass, Instance)
        self._superclass = superclass
        self._superclass._add_subclass(self)

    def _add_subclass(self, INSTANCE):
        assert isinstance(INSTANCE, Instance)
        self._subclasses.append(INSTANCE)

    def _all_subclasses(self):
        """
        Transitive closure on self._subclasses.

        Return a set containing all direct and indirect subclasses,
        including itself.
        """
        res = set()
        stack = [self]
        while stack:
            item = stack.pop()
            res.add(item)
            stack += item._subclasses
        return res

    def _add_fields(self, fields, with_default=False):
        fields = fields.copy()    # mutated below
        for name, defn in fields.iteritems():
            _, meth = self._lookup(name)
            if meth is not None:
                raise TypeError("Cannot add field %r: method already exists" % name)
        
            if self._superclass is not None:
                if self._superclass._has_field(name):
                    raise TypeError("Field %r exists in superclass" % name)

            if type(defn) is not tuple:
                if isinstance(defn, Meth):
                    raise TypeError("Attempting to store method in field")
                
                fields[name] = (defn, defn._defl())
            else:
                ootype, default = defn

                if isinstance(ootype, Meth):
                    raise TypeError("Attempting to store method in field")

                if ootype != typeOf(default):
                    raise TypeError("Expected type %r for default" % (ootype,))

        self._fields.update(fields)
        if with_default:
            self._fields_with_default.extend(fields.items())

    def _override_default_for_fields(self, fields):
        # sanity check
        for field in fields:
            INST, TYPE = self._superclass._lookup_field(field)
            assert TYPE is not None, "Can't find field %s in superclasses" % field
        self._overridden_defaults.update(fields)

    def _add_methods(self, methods):
        # Note to the unwary: _add_methods adds *methods* whereas
        # _add_fields adds *descriptions* of fields.  This is obvious
        # if you are in the right state of mind (swiss?), but
        # certainly not necessarily if not.
        for name, method in methods.iteritems():
            if self._has_field(name):
                raise TypeError("Can't add method %r: field already exists" % name)
            if not isinstance(typeOf(method), Meth):
                raise TypeError("added methods must be _meths, not %s" % type(method))
        self._methods.update(methods)

    def _init_instance(self, instance):
        if self._superclass is not None:
            self._superclass._init_instance(instance)
        
        for name, (ootype, default) in self._fields.iteritems():
            instance.__dict__[name] = enforce(ootype, default)

        for name, (ootype, default) in self._overridden_defaults.iteritems():
            instance.__dict__[name] = enforce(ootype, default)

    def _has_field(self, name):
        try:
            self._fields[name]
            return True
        except KeyError:
            if self._superclass is None:
                return False

            return self._superclass._has_field(name)

    def _field_type(self, name):
        try:
            return self._fields[name][0]
        except KeyError:
            if self._superclass is None:
                raise TypeError("No field names %r" % name)

            return self._superclass._field_type(name)

    _check_field = _field_type

    def _lookup_field(self, name):
        field = self._fields.get(name)

        if field is None and self._superclass is not None:
            return self._superclass._lookup_field(name)

        try:
            return self, field[0]
        except TypeError:
            return self, None

    def _lookup(self, meth_name):
        meth = self._methods.get(meth_name)

        if meth is None and self._superclass is not None:
            return self._superclass._lookup(meth_name)

        return self, meth

    def _allfields(self):
        if self._superclass is None:
            all = {}
        else:
            all = self._superclass._allfields()
        all.update(self._fields)
        return all

    def _lookup_graphs(self, meth_name):
        _, meth = self._lookup(meth_name)
        graphs = set()
        if not getattr(meth, 'abstract', False):
            graphs.add(meth.graph)
        for SUBTYPE in self._subclasses:
            graphs.update(SUBTYPE._lookup_graphs(meth_name))
        return graphs

    def _get_fields_with_default(self):
        if self._superclass is None:
            return self._fields_with_default[:]
        return self._superclass._get_fields_with_default() + self._fields_with_default

    def _immutable_field(self, field):
        if self._hints.get('immutable'):
            return True
        if 'immutable_fields' in self._hints:
            try:
                return self._hints['immutable_fields'].fields[field]
            except KeyError:
                pass
        return False


class SpecializableType(OOType):
    def _specialize_type(self, TYPE, generic_types):
        if isinstance(TYPE, SpecializableType):
            res = TYPE._specialize(generic_types)
        else:
            res = generic_types.get(TYPE, TYPE)
        assert res is not None
        return res

    def _specialize(self, generic_types):
        raise NotImplementedError

class StaticMethod(SpecializableType):

    def __init__(self, args, result):
        self.ARGS = tuple(args)
        self.RESULT = result
        self._null = _null_static_meth(self)

    def _example(self):
        _retval = self.RESULT._example()
        return _static_meth(self, _callable=lambda *args: _retval)

    def _defl(self):
        return null(self)

    def __repr__(self):
        return "<%s(%s, %s)>" % (self.__class__.__name__, list(self.ARGS), self.RESULT)

    __str__ = __repr__

    def _specialize(self, generic_types):
        ARGS = tuple([self._specialize_type(ARG, generic_types)
                      for ARG in self.ARGS])
        RESULT = self._specialize_type(self.RESULT, generic_types)
        return self.__class__(ARGS, RESULT)


class Meth(StaticMethod):

    SELFTYPE = None

    def __init__(self, args, result):
        StaticMethod.__init__(self, args, result)


class BuiltinType(SpecializableType):

    def _example(self):
        return new(self)

    def _defl(self):
        return self._null

    def _get_interp_class(self):
        raise NotImplementedError

class Record(BuiltinType):

    # We try to keep Record as similar to Instance as possible, so backends
    # can treat them polymorphically, if they choose to do so.

    def __init__(self, fields, _hints={}):
        if isinstance(fields, dict):
            fields = fields.items()    # random order in that case
        self._fields = frozendict()
        fields_in_order = []
        for name, ITEMTYPE in fields:
            self._fields[name] = ITEMTYPE, ITEMTYPE._defl()
            fields_in_order.append(name)
        self._fields_in_order = tuple(fields_in_order)
        self._null = _null_record(self)
        self._hints = frozendict(_hints)

    def _defl(self):
        return self._null

    def _get_interp_class(self):
        return _record

    def _field_type(self, name):
        try:
            return self._fields[name][0]
        except KeyError:
            raise TypeError("No field names %r" % name)

    _check_field = _field_type

    def _lookup(self, meth_name):
        return self, None

    def _lookup_field(self, name):
        try:
            return self, self._field_type(name)
        except TypeError:
            return self, None

    def __str__(self):
        item_str = ["%s: %s" % (str(name), str(self._fields[name][0]))
                    for name in self._fields_in_order]
        return '%s(%s)' % (self.__class__.__name__, ", ".join(item_str))

class BuiltinADTType(BuiltinType):

    immutable = False # conservative

    def _setup_methods(self, generic_types, can_raise=[], pure_meth=[]):
        methods = {}
        for name, meth in self._GENERIC_METHODS.iteritems():
            args = [self._specialize_type(arg, generic_types) for arg in meth.ARGS]
            result = self._specialize_type(meth.RESULT, generic_types)
            METH = Meth(args, result)
            METH.SELFTYPE = self
            methods[name] = METH
        self._METHODS = frozendict(methods)
        self._can_raise = tuple(can_raise)
        if pure_meth == 'ALL':
            self._pure_meth = tuple(methods.keys())
        else:
            self._pure_meth = tuple(pure_meth)

    def _lookup(self, meth_name):
        METH = self._METHODS.get(meth_name)
        meth = None
        if METH is not None:
            cls = self._get_interp_class()
            can_raise = meth_name in self._can_raise
            pure_meth = meth_name in self._pure_meth
            meth = _meth(METH, _name=meth_name,
                         _callable=getattr(cls, meth_name),
                         _can_raise=can_raise, _pure_meth=pure_meth)
            meth._virtual = False
        return self, meth

    def _lookup_graphs(self, meth_name):
        return set()


class AbstractString(BuiltinADTType):

    oopspec_name = 'str'
    immutable = True

    def __init__(self):
        self._null = _null_string(self)

        generic_types = { self.SELFTYPE_T: self }
        self._GENERIC_METHODS = frozendict({
            "ll_hash": Meth([], Signed),
            "ll_stritem_nonneg": Meth([Signed], self.CHAR),
            "ll_strlen": Meth([], Signed),
            "ll_strconcat": Meth([self.SELFTYPE_T], self.SELFTYPE_T),
            "ll_streq": Meth([self.SELFTYPE_T], Bool),
            "ll_strcmp": Meth([self.SELFTYPE_T], Signed),
            "ll_startswith": Meth([self.SELFTYPE_T], Bool),
            "ll_endswith": Meth([self.SELFTYPE_T], Bool),
            "ll_find": Meth([self.SELFTYPE_T, Signed, Signed], Signed),
            "ll_rfind": Meth([self.SELFTYPE_T, Signed, Signed], Signed),
            "ll_count": Meth([self.SELFTYPE_T, Signed, Signed], Signed),
            "ll_find_char": Meth([self.CHAR, Signed, Signed], Signed),
            "ll_rfind_char": Meth([self.CHAR, Signed, Signed], Signed),
            "ll_count_char": Meth([self.CHAR, Signed, Signed], Signed),
            "ll_strip": Meth([self.CHAR, Bool, Bool], self.SELFTYPE_T),
            "ll_upper": Meth([], self.SELFTYPE_T),
            "ll_lower": Meth([], self.SELFTYPE_T),
            "ll_substring": Meth([Signed, Signed], self.SELFTYPE_T), # ll_substring(start, count)
            "ll_split_chr": Meth([self.CHAR, Signed], Array(self.SELFTYPE_T)), # XXX this is not pure!
            "ll_rsplit_chr": Meth([self.CHAR, Signed], Array(self.SELFTYPE_T)), # XXX this is not pure!
            "ll_contains": Meth([self.CHAR], Bool),
            "ll_replace_chr_chr": Meth([self.CHAR, self.CHAR], self.SELFTYPE_T),
            })
        self._setup_methods(generic_types, pure_meth='ALL')

    def _example(self):
        return self._defl()

    def _get_interp_class(self):
        return _string

    def _specialize(self, generic_types):
        return self

# WARNING: the name 'String' is rebound at the end of file
class String(AbstractString):
    SELFTYPE_T = object()
    CHAR = Char
    _name = 'String'

    # TODO: should it return _null or ''?
    def _defl(self):
        return make_string('')

    def _enforce(self, value):
        # XXX share this with Unicode?
        TYPE = typeOf(value)
        if TYPE == self.CHAR:
            return make_string(value)
        else:
            return BuiltinADTType._enforce(self, value)


# WARNING: the name 'Unicode' is rebound at the end of file
class Unicode(AbstractString):
    SELFTYPE_T = object()
    CHAR = UniChar
    _name = 'Unicode'

    # TODO: should it return _null or ''?
    def _defl(self):
        return make_unicode(u'')

    def _enforce(self, value):
        TYPE = typeOf(value)
        if TYPE == self.CHAR:
            return make_unicode(value)
        else:
            return BuiltinADTType._enforce(self, value)




# WARNING: the name 'StringBuilder' is rebound at the end of file
class StringBuilder(BuiltinADTType):
    oopspec_name = 'stringbuilder'

    def __init__(self, STRINGTP, CHARTP):
        self._null = _null_string_builder(self)
        self._GENERIC_METHODS = frozendict({
            "ll_allocate": Meth([Signed], Void),
            "ll_append_char": Meth([CHARTP], Void),
            "ll_append": Meth([STRINGTP], Void),
            "ll_build": Meth([], STRINGTP),
            })
        self._setup_methods({})

    def _defl(self):
        return self._null

    def _get_interp_class(self):
        return _string_builder

    def _specialize(self, generic_types):
        return self

# WARNING: the name WeakReference is rebound at the end of file
class WeakReference(BuiltinADTType):
    def __init__(self):
        self._null = _null_weak_reference(self)
        self._GENERIC_METHODS = frozendict({
            "ll_set": Meth([ROOT], Void),
            "ll_deref": Meth([], ROOT),
            })
        self._setup_methods({})

    def _defl(self):
        return self._null

    def _get_interp_class(self):
        return _weak_reference

    def _specialize(self, generic_types):
        return self

class List(BuiltinADTType):
    # placeholders for types
    # make sure that each derived class has his own SELFTYPE_T
    # placeholder, because we want backends to distinguish that.
    SELFTYPE_T = object()
    ITEMTYPE_T = object()
    oopspec_name = 'list'
    oopspec_new = 'new(0)'
    oopspec_new_argnames = ()

    def __init__(self, ITEMTYPE=None):
        self.ITEM = ITEMTYPE
        self._null = _null_list(self)
        if ITEMTYPE is not None:
            self._init_methods()

    def _init_methods(self):
        # This defines the abstract list interface that backends will
        # have to map to their native list implementations.
        # 'ITEMTYPE_T' is used as a placeholder for indicating
        # arguments that should have ITEMTYPE type. 'SELFTYPE_T' indicates 'self'

        generic_types = {
            self.SELFTYPE_T: self,
            self.ITEMTYPE_T: self.ITEM,
            }

        # the methods are named after the ADT methods of lltypesystem's lists
        self._GENERIC_METHODS = frozendict({
            # "name": Meth([ARGUMENT1_TYPE, ARGUMENT2_TYPE, ...], RESULT_TYPE)
            "ll_length": Meth([], Signed),
            "ll_getitem_fast": Meth([Signed], self.ITEMTYPE_T),
            "ll_setitem_fast": Meth([Signed, self.ITEMTYPE_T], Void),
            "_ll_resize_ge": Meth([Signed], Void),
            "_ll_resize_le": Meth([Signed], Void),
            "_ll_resize": Meth([Signed], Void),
        })

        self._setup_methods(generic_types)

    # this is the equivalent of the lltypesystem ll_newlist that is
    # marked as typeMethod.
    def ll_newlist(self, length):
        from pypy.rpython.ootypesystem import rlist
        return rlist.ll_newlist(self, length)
    ll_newlist._annenforceargs_ = (None, int)

    # NB: We are expecting Lists of the same ITEMTYPE to compare/hash
    # equal. We don't redefine __eq__/__hash__ since the implementations
    # from LowLevelType work fine, especially in the face of recursive
    # data structures. But it is important to make sure that attributes
    # of supposedly equal Lists compare/hash equal.

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, List):
            return False
        if self.ITEM is None or other.ITEM is None:
            return False # behave like a ForwardReference, i.e. compare by identity
        return BuiltinADTType.__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self.ITEM is None:
            raise TypeError("Can't hash uninitialized List type.")
        return BuiltinADTType.__hash__(self)    

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__,
                saferecursive(str, "...")(self.ITEM))

    def _get_interp_class(self):
        return _list

    def _specialize(self, generic_types):
        ITEMTYPE = self._specialize_type(self.ITEM, generic_types)
        return self.__class__(ITEMTYPE)
    
    def _defl(self):
        return self._null

    def _set_itemtype(self, ITEMTYPE):
        self.ITEM = ITEMTYPE
        self._init_methods()

    def ll_convert_from_array(self, array):
        length = array.ll_length()
        result = self.ll_newlist(length)
        for n in range(length):
            result.ll_setitem_fast(n, array.ll_getitem_fast(n))
        return result

class Array(BuiltinADTType):
    # placeholders for types
    # make sure that each derived class has his own SELFTYPE_T
    # placeholder, because we want backends to distinguish that.
    
    SELFTYPE_T = object()
    ITEMTYPE_T = object()
    oopspec_name = 'list'
    oopspec_new = 'new(length)'
    oopspec_new_argnames = ('length',)

    def __init__(self, ITEMTYPE=None, _hints = {}):
        self.ITEM = ITEMTYPE
        self._hints = frozendict(_hints)
        self._null = _null_array(self)
        if ITEMTYPE is not None:
            self._init_methods()

    def _init_methods(self):
        # This defines the abstract list interface that backends will
        # have to map to their native list implementations.
        # 'ITEMTYPE_T' is used as a placeholder for indicating
        # arguments that should have ITEMTYPE type. 'SELFTYPE_T' indicates 'self'

        generic_types = {
            self.SELFTYPE_T: self,
            self.ITEMTYPE_T: self.ITEM,
            }

        # the methods are named after the ADT methods of lltypesystem's lists
        self._GENERIC_METHODS = frozendict({
            # "name": Meth([ARGUMENT1_TYPE, ARGUMENT2_TYPE, ...], RESULT_TYPE)
            "ll_length": Meth([], Signed),
            "ll_getitem_fast": Meth([Signed], self.ITEMTYPE_T),
            "ll_setitem_fast": Meth([Signed, self.ITEMTYPE_T], Void),
        })

        self._setup_methods(generic_types)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Array):
            return False
        if self.ITEM is None or other.ITEM is None:
            return False # behave like a ForwardReference, i.e. compare by identity
        return BuiltinADTType.__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self.ITEM is None:
            raise TypeError("Can't hash uninitialized List type.")
        return BuiltinADTType.__hash__(self)    

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__,
                saferecursive(str, "...")(self.ITEM))

    def _get_interp_class(self):
        return _array

    def _specialize(self, generic_types):
        ITEMTYPE = self._specialize_type(self.ITEM, generic_types)
        return self.__class__(ITEMTYPE)

    def _defl(self):
        return self._null

    def _example(self):
        return oonewarray(self, 1)

    def _set_itemtype(self, ITEMTYPE):
        self.ITEM = ITEMTYPE
        self._init_methods()

    def ll_newlist(self, length):
        from pypy.rpython.ootypesystem import rlist
        return rlist.ll_newarray(self, length)
    ll_newlist._annenforceargs_ = (None, int)

    def ll_convert_from_array(self, array):
        return array

class Dict(BuiltinADTType):
    # placeholders for types
    SELFTYPE_T = object()
    KEYTYPE_T = object()
    VALUETYPE_T = object()
    oopspec_name = 'dict'
    oopspec_new = 'new()'
    oopspec_new_argnames = ()

    def __init__(self, KEYTYPE=None, VALUETYPE=None):
        self._KEYTYPE = KEYTYPE
        self._VALUETYPE = VALUETYPE
        self._null = _null_dict(self)

        if self._is_initialized():
            self._init_methods()

    def _is_initialized(self):
        return self._KEYTYPE is not None and self._VALUETYPE is not None

    def _init_methods(self):
        # XXX clean-up later! Rename _KEYTYPE and _VALUETYPE to KEY and VALUE.
        # For now they are just synonyms, please use KEY/VALUE in new code.
        self.KEY = self._KEYTYPE
        self.VALUE = self._VALUETYPE

        self._generic_types = frozendict({
            self.SELFTYPE_T: self,
            self.KEYTYPE_T: self._KEYTYPE,
            self.VALUETYPE_T: self._VALUETYPE
            })

        # ll_get() is always used just after a call to ll_contains(),
        # always with the same key, so backends can optimize/cache the
        # result
        self._GENERIC_METHODS = frozendict({
            "ll_length": Meth([], Signed),
            "ll_get": Meth([self.KEYTYPE_T], self.VALUETYPE_T),
            "ll_set": Meth([self.KEYTYPE_T, self.VALUETYPE_T], Void),
            "ll_remove": Meth([self.KEYTYPE_T], Bool), # return False is key was not present
            "ll_contains": Meth([self.KEYTYPE_T], Bool),
            "ll_clear": Meth([], Void),
            "ll_get_items_iterator": Meth([], DictItemsIterator(self.KEYTYPE_T, self.VALUETYPE_T)),
        })

        self._setup_methods(self._generic_types)

    # NB: We are expecting Dicts of the same KEYTYPE, VALUETYPE to
    # compare/hash equal. We don't redefine __eq__/__hash__ since the
    # implementations from LowLevelType work fine, especially in the
    # face of recursive data structures. But it is important to make
    # sure that attributes of supposedly equal Dicts compare/hash
    # equal.

    def __str__(self):
        return '%s(%s, %s)' % (self.__class__.__name__,
                self._KEYTYPE, saferecursive(str, "...")(self._VALUETYPE))

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Dict):
            return False
        if not self._is_initialized() or not other._is_initialized():
            return False # behave like a ForwardReference, i.e. compare by identity
        return BuiltinADTType.__eq__(self, other) 

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if not self._is_initialized():
            raise TypeError("Can't hash uninitialized Dict type.")
        return BuiltinADTType.__hash__(self)

    def _get_interp_class(self):
        return _dict

    def _specialize(self, generic_types):
        KEYTYPE = self._specialize_type(self._KEYTYPE, generic_types)
        VALUETYPE = self._specialize_type(self._VALUETYPE, generic_types)
        return self.__class__(KEYTYPE, VALUETYPE)

    def _set_types(self, KEYTYPE, VALUETYPE):
        self._KEYTYPE = KEYTYPE
        self._VALUETYPE = VALUETYPE
        self._init_methods()
                                           

class CustomDict(Dict):
    def __init__(self, KEYTYPE=None, VALUETYPE=None):
        Dict.__init__(self, KEYTYPE, VALUETYPE)
        self._null = _null_custom_dict(self)

        if self._is_initialized():
            self._init_methods()

    def _init_methods(self):
        Dict._init_methods(self)
        EQ_FUNC = StaticMethod([self.KEYTYPE_T, self.KEYTYPE_T], Bool)
        HASH_FUNC = StaticMethod([self.KEYTYPE_T], Signed)
        self._GENERIC_METHODS['ll_set_functions'] = Meth([EQ_FUNC, HASH_FUNC], Void)
        self._GENERIC_METHODS['ll_copy'] = Meth([], self.SELFTYPE_T)
        self._setup_methods(self._generic_types, can_raise=['ll_get', 'll_set', 'll_remove', 'll_contains'])

    def _get_interp_class(self):
        return _custom_dict


class DictItemsIterator(BuiltinADTType):
    SELFTYPE_T = object()
    KEYTYPE_T = object()
    VALUETYPE_T = object()

    def __init__(self, KEYTYPE, VALUETYPE):
        self._KEYTYPE = KEYTYPE
        self._VALUETYPE = VALUETYPE
        self._null = _null_dict_items_iterator(self)

        generic_types = {
            self.SELFTYPE_T: self,
            self.KEYTYPE_T: KEYTYPE,
            self.VALUETYPE_T: VALUETYPE
            }

        # Dictionaries are not allowed to be changed during an
        # iteration. The ll_go_next method should check this condition
        # and raise RuntimeError in that case.
        self._GENERIC_METHODS = frozendict({
            "ll_go_next": Meth([], Bool), # move forward; return False is there is no more data available
            "ll_current_key": Meth([], self.KEYTYPE_T),
            "ll_current_value": Meth([], self.VALUETYPE_T),
        })
        self._setup_methods(generic_types, can_raise=['ll_go_next'])

    def __str__(self):
        return '%s%s' % (self.__class__.__name__,
                saferecursive(str, "(...)")((self._KEYTYPE, self._VALUETYPE)))

    def _get_interp_class(self):
        return _dict_items_iterator

    def _specialize(self, generic_types):
        KEYTYPE = self._specialize_type(self._KEYTYPE, generic_types)
        VALUETYPE = self._specialize_type(self._VALUETYPE, generic_types)
        return self.__class__(KEYTYPE, VALUETYPE)
    
# ____________________________________________________________

class _object(object):

    def __init__(self, obj):
        self._TYPE = Object
        assert obj is None or obj, 'Cannot create _object of a null value, use make_object() instead'
        self.obj = obj

    def __nonzero__(self):
        return self.obj is not None

    def __eq__(self, other):
        if not isinstance(other, _object):
            raise TypeError("comparing an _object with %r" % other)
        if self.obj is None:
            return other.obj is None
        elif other.obj is None:
            return self.obj is None
        else:
            return self.obj.__class__ == other.obj.__class__ and \
                   self.obj == other.obj

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.obj)

    def _identityhash(self):
        try:
            return self.obj._identityhash()
        except AttributeError:
            return hash(self.obj)

    def _cast_to_object(self):
        return self

    def _cast_to(self, EXPECTED_TYPE):
        if self.obj is None:
            return null(EXPECTED_TYPE)
        elif EXPECTED_TYPE is Object:
            return self
        elif isinstance(EXPECTED_TYPE, Instance):
            return oodowncast(EXPECTED_TYPE, self.obj)
        else:
            T = typeOf(self.obj)
            if T != EXPECTED_TYPE:
                raise RuntimeError("Invalid cast: %s --> %s" % (T, EXPECTED_TYPE))
            return self.obj


class _class(object):
    _TYPE = Class

    def __init__(self, INSTANCE):
        self._INSTANCE = INSTANCE

    def _cast_to_object(self):
        return make_object(self)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE)

    def __nonzero__(self):
        return self._INSTANCE is not None

nullruntimeclass = _class(None)
Class._null = nullruntimeclass

class _instance(object):
    
    def __init__(self, INSTANCE):
        self.__dict__["_TYPE"] = INSTANCE
        INSTANCE._init_instance(self)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%r inst at 0x%x' % (self._TYPE._name, uid(self))

    def __getattr__(self, name):
        DEFINST, meth = self._TYPE._lookup(name)
        if meth is not None:
            return meth._bound(DEFINST, self)
        
        self._TYPE._check_field(name)

        return self.__dict__[name]

    def __setattr__(self, name, value):
        self.__getattr__(name)

        FLDTYPE = self._TYPE._field_type(name)
        try:
            val = enforce(FLDTYPE, value)
        except TypeError:
            raise TypeError("Expected type %r" % FLDTYPE)

        self.__dict__[name] = value

    def __nonzero__(self):
        return True    # better be explicit -- overridden in _null_instance

    def __eq__(self, other):
        if not isinstance(other, _instance):
            raise TypeError("comparing an _instance with %r" % (other,))
        return self is other   # same comment as __nonzero__

    def __ne__(self, other):
        return not (self == other)

    def _instanceof(self, INSTANCE):
        assert isinstance(INSTANCE, Instance)
        return bool(self) and isSubclass(self._TYPE, INSTANCE)

    def _classof(self):
        assert bool(self)
        return runtimeClass(self._TYPE)

    def _upcast(self, INSTANCE):
        assert instanceof(self, INSTANCE)
        return self

    _enforce = _upcast
    
    def _downcast(self, INSTANCE):
        assert instanceof(self, INSTANCE)
        return self

    def _identityhash(self):
        return hash(self)

    def _cast_to_object(self):
        return make_object(ooupcast(ROOT, self))


def _null_mixin(klass):
    class mixin(object):

        def __str__(self):
            try:
                name = self._TYPE._name
            except AttributeError:
                name = self._TYPE
            return '%r null inst' % (name,)

        def __getattribute__(self, name):
            if name.startswith("_"):
                return object.__getattribute__(self, name)
        
            raise RuntimeError("Access to field in null object")

        def __setattr__(self, name, value):
            klass.__setattr__(self, name, value)

            raise RuntimeError("Assignment to field in null object")

        def __nonzero__(self):
            return False

        def __eq__(self, other):
            if not isinstance(other, klass):
                raise TypeError("comparing an %s with %r" % (klass.__name__, other))
            return not other

        def __ne__(self, other):
            return not (self == other)

        def __hash__(self):
            return hash(self._TYPE)
    return mixin

class _null_instance(_null_mixin(_instance), _instance):

    def __init__(self, INSTANCE):
        self.__dict__["_TYPE"] = INSTANCE


class _view(object):

    def __init__(self, INSTANCE, inst):
        self.__dict__['_TYPE'] = INSTANCE
        assert isinstance(inst, (_instance, _record))
        assert isinstance(inst._TYPE, Record) or isSubclass(inst._TYPE, INSTANCE)
        self.__dict__['_inst'] = inst

    def __repr__(self):
        if self._TYPE == self._inst._TYPE:
            return repr(self._inst)
        else:
            return '<%r view of %s>' % (self._TYPE._name, self._inst)

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if not isinstance(other, _view):
            return False
        a = self._inst
        b = other._inst
        return a.__class__ == b.__class__ and a == b

    def __hash__(self):
        return hash(self._inst) + 1

    def __nonzero__(self):
        return bool(self._inst)

    def __setattr__(self, name, value):
        self._TYPE._check_field(name)
        setattr(self._inst, name, value)

    def __getattr__(self, name):
        _, meth = self._TYPE._lookup(name)
        meth or self._TYPE._check_field(name)
        res = getattr(self._inst, name)
        if meth:
            assert isinstance(res, _bound_meth)
            return res.__class__(res.DEFINST, _view(res.DEFINST, res.inst), res.meth)
        return res

    def _become(self, other):
        assert self._TYPE == other._TYPE
        assert isinstance(other, _view)
        self.__dict__['_inst'] = other._inst

    def _instanceof(self, INSTANCE):
        return self._inst._instanceof(INSTANCE)

    def _classof(self):
        return self._inst._classof()

    def _upcast(self, INSTANCE):
        assert isSubclass(self._TYPE, INSTANCE)
        return _view(INSTANCE, self._inst)

    _enforce = _upcast

    def _downcast(self, INSTANCE):
        if not self._inst:
            assert isSubclass(INSTANCE, self._TYPE) or isSubclass(self._TYPE, INSTANCE)
            return null(INSTANCE)
        assert isSubclass(INSTANCE, self._TYPE)
        return _view(INSTANCE, self._inst)

    def _identityhash(self):
        return self._inst._identityhash()

    def _cast_to_object(self):
        return make_object(ooupcast(ROOT, self))

if STATICNESS:
    instance_impl = _view
else:
    instance_impl = _instance

def make_string(value):
    assert isinstance(value, str)
    return _string(String, value)

def make_unicode(value):
    assert isinstance(value, unicode)
    return _string(Unicode, value)

def make_instance(INSTANCE):
    inst = _instance(INSTANCE)
    if STATICNESS:
        inst = _view(INSTANCE, inst)
    return inst

def make_null_instance(INSTANCE):
    inst = _null_instance(INSTANCE)
    if STATICNESS:
        inst = _view(INSTANCE, inst)
    return inst

def make_object(llvalue):
    if llvalue:
        return _object(llvalue)
    else:
        return NULL

class _callable(object):

   def __init__(self, TYPE, **attrs):
       self._TYPE = TYPE
       self._name = "?"
       self._callable = None
       self.__dict__.update(attrs)

   def _checkargs(self, args, check_callable=True):
       if len(args) != len(self._TYPE.ARGS):
           raise TypeError,"calling %r with wrong argument number: %r" % (self._TYPE, args)

       checked_args = []
       for a, ARG in zip(args, self._TYPE.ARGS):
           try:
               if ARG is not Void:
                   a = enforce(ARG, a)
           except TypeError:
               raise TypeError,"calling %r with wrong argument types: %r" % (self._TYPE, args)
           checked_args.append(a)
       if not check_callable:
           return checked_args
       callb = self._callable
       if callb is None:
           raise RuntimeError,"calling undefined or null function"
       return callb, checked_args

   def __eq__(self, other):
       return (self.__class__ is other.__class__ and
               self.__dict__ == other.__dict__)

   def __ne__(self, other):
       return not (self == other)
   
   def __hash__(self):
       return hash(frozendict(self.__dict__))

   def _cast_to_object(self):
       return make_object(self)


class _static_meth(_callable):
   allowed_types = (StaticMethod,)

   def __init__(self, STATICMETHOD, **attrs):
       assert isinstance(STATICMETHOD, self.allowed_types)
       _callable.__init__(self, STATICMETHOD, **attrs)

   def __call__(self, *args):
       callb, checked_args = self._checkargs(args)
       return callb(*checked_args)

   def __repr__(self):
       return 'sm %s' % self._name

   def _as_ptr(self):
       return self

class _null_static_meth(_null_mixin(_static_meth), _static_meth):

    def __init__(self, STATICMETHOD):
        self.__dict__["_TYPE"] = STATICMETHOD
        self.__dict__["_name"] = "? (null)"
        self.__dict__["_callable"] = None


class _forward_static_meth(_static_meth):
   allowed_types = (StaticMethod, ForwardReference)

   def __eq__(self, other):
       return self is other
   
   def __hash__(self):
       return id(self)

   def _become(self, other):
       assert isinstance(other, _static_meth)
       self.__dict__ = other.__dict__

class _bound_meth(object):
    def __init__(self, DEFINST, inst, meth):
        self.DEFINST = DEFINST
        self.inst = inst
        self.meth = meth

    def __call__(self, *args):
        callb, checked_args = self.meth._checkargs(args)
        return callb(self.inst, *checked_args)

    def _cast_to_object(self):
        return make_object(self)


class _meth(_callable):
    _bound_class = _bound_meth
    
    def __init__(self, METHOD, **attrs):
        assert isinstance(METHOD, Meth)
        _callable.__init__(self, METHOD, **attrs)

    def _bound(self, DEFINST, inst):
        TYPE = typeOf(inst)
        assert isinstance(TYPE, (Instance, BuiltinType))
        return self._bound_class(DEFINST, inst, self)


class _overloaded_meth_desc:
    def __init__(self, name, TYPE):
        self.name = name
        self.TYPE = TYPE


class _overloaded_bound_meth(_bound_meth):
    def __init__(self, DEFINST, inst, meth):
        self.DEFINST = DEFINST
        self.inst = inst
        self.meth = meth

    def _get_bound_meth(self, *args):
        ARGS = tuple([typeOf(arg) for arg in args])
        meth = self.meth._resolver.resolve(ARGS)
        assert isinstance(meth, _meth)
        return meth._bound(self.DEFINST, self.inst)

    def __call__(self, *args):
        bound_meth = self._get_bound_meth(*args)
        return bound_meth(*args)


class OverloadingResolver(object):

    def __init__(self, overloadings):
        self.overloadings = overloadings
        self._check_overloadings()

    def _check_overloadings(self):
        signatures = py.builtin.set()
        for meth in self.overloadings:
            ARGS = meth._TYPE.ARGS
            if ARGS in signatures:
                raise TypeError, 'Bad overloading'
            signatures.add(ARGS)

    def annotate(self, args_s):
        ARGS = tuple([self.annotation_to_lltype(arg_s) for arg_s in args_s])
        METH = self.resolve(ARGS)._TYPE
        return self.lltype_to_annotation(METH.RESULT)

    def resolve(self, ARGS):
        # this overloading resolution algorithm is quite simple:
        # 1) if there is an exact match between ARGS and meth.ARGS, return meth
        # 2) if there is *only one* meth such as ARGS can be converted
        #    to meth.ARGS with one or more upcasts, return meth
        # 3) otherwise, fail
        matches = []
        for meth in self.overloadings:
            METH = meth._TYPE
            if METH.ARGS == ARGS:
                return meth # case 1
            elif self._check_signature(ARGS, METH.ARGS):
                matches.append(meth)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise TypeError, 'More than one method match, please use explicit casts'
        else:
            raise TypeError, 'No suitable overloading found for method'

    def _check_signature(self, ARGS1, ARGS2):
        if len(ARGS1) != len(ARGS2):
            return False
        for ARG1, ARG2 in zip(ARGS1, ARGS2):
            if not self._can_convert_from_to(ARG1, ARG2):
                return False
        return True

    def _can_convert_from_to(self, ARG1, ARG2):
        if isinstance(ARG1, Instance) and isinstance(ARG2, Instance) and isSubclass(ARG1, ARG2):
            return True
        else:
            return False
    
    def annotation_to_lltype(cls, ann):
        from pypy.annotation import model as annmodel
        return annmodel.annotation_to_lltype(ann)
    annotation_to_lltype = classmethod(annotation_to_lltype)

    def lltype_to_annotation(cls, TYPE):
        from pypy.annotation import model as annmodel
        return annmodel.lltype_to_annotation(TYPE)
    lltype_to_annotation = classmethod(lltype_to_annotation)


class _overloaded_meth(_meth):
    _bound_class = _overloaded_bound_meth
    _desc_class = _overloaded_meth_desc

    def __init__(self, *overloadings, **attrs):
        assert '_callable' not in attrs
        resolver = attrs.pop('resolver', OverloadingResolver)
        _meth.__init__(self, Meth([], Void), _callable=None, **attrs) # use a fake method type
        self._resolver = resolver(overloadings)

    def _get_desc(self, name, ARGS):
        meth = self._resolver.resolve(ARGS)
        return _overloaded_meth_desc(name, meth._TYPE)


class _builtin_type(object):
    def __getattribute__(self, name):
        TYPE = object.__getattribute__(self, "_TYPE")
        _, meth = TYPE._lookup(name)
        if meth is not None:
            res = meth._bound(TYPE, self)
            res._name = name
            return res

        return object.__getattribute__(self, name)

    def _cast_to_object(self):
        return make_object(self)

class _string(_builtin_type):

    def __init__(self, STRING, value = ''):
        self._str = value
        self._TYPE = STRING

    def __hash__(self):
        return hash(self._str)

    def __cmp__(self, other):
        return cmp(self._str, other._str)

    def __repr__(self):
        return 'ootype._string(value=%r)' % self._str

    def make_string(self, value):
        if self._TYPE is String:
            return make_string(value)
        elif self._TYPE is Unicode:
            return make_unicode(value)
        else:
            assert False, 'Unknown type %s' % self._TYPE

    def ll_hash(self):
        # NOT_RPYTHON
        # hopefully, ll_hash() should not be called on NULL
        assert self._str is not None
        return objectmodel._hash_string(self._str)

    def ll_stritem_nonneg(self, i):
        # NOT_RPYTHON
        s = self._str
        assert 0 <= i < len(s)
        return s[i]

    def ll_strlen(self):
        # NOT_RPYTHON
        return len(self._str)

    def ll_strconcat(self, s):
        # NOT_RPYTHON
        return self.make_string(self._str + s._str)

    def ll_streq(self, s):
        # NOT_RPYTON
        return self._str == s._str

    def ll_strcmp(self, s):
        # NOT_RPYTHON
        return cmp(self._str, s._str)

    def ll_startswith(self, s):
        # NOT_RPYTHON
        return self._str.startswith(s._str)

    def ll_endswith(self, s):
        # NOT_RPYTHON
        return self._str.endswith(s._str)

    def ll_find(self, s, start, end):
        # NOT_RPYTHON
        if start > len(self._str):  # workaround to cope with corner case
            return -1               # bugs in CPython 2.4 unicode.find('')
        return self._str.find(s._str, start, end)

    def ll_rfind(self, s, start, end):
        # NOT_RPYTHON
        if start > len(self._str):  # workaround to cope with corner case
            return -1               # bugs in CPython 2.4 unicode.rfind('')
        return self._str.rfind(s._str, start, end)

    def ll_count(self, s, start, end):
        # NOT_RPYTHON
        return self._str.count(s._str, start, end)

    def ll_find_char(self, ch, start, end):
        # NOT_RPYTHON
        return self._str.find(ch, start, end)

    def ll_rfind_char(self, ch, start, end):
        # NOT_RPYTHON
        return self._str.rfind(ch, start, end)

    def ll_count_char(self, ch, start, end):
        # NOT_RPYTHON
        return self._str.count(ch, start, end)

    def ll_strip(self, ch, left, right):
        # NOT_RPYTHON
        s = self._str
        if left:
            s = s.lstrip(ch)
        if right:
            s = s.rstrip(ch)
        return self.make_string(s)

    def ll_upper(self):
        # NOT_RPYTHON
        return self.make_string(self._str.upper())

    def ll_lower(self):
        # NOT_RPYTHON
        return self.make_string(self._str.lower())

    def ll_substring(self, start, count):
        # NOT_RPYTHON
        return self.make_string(self._str[start:start+count])

    def ll_split_chr(self, ch, max):
        # NOT_RPYTHON
        l = [self.make_string(s) for s in self._str.split(ch, max)]
        res = _array(Array(self._TYPE), len(l))
        res._array[:] = l
        return res

    def ll_rsplit_chr(self, ch, max):
        # NOT_RPYTHON
        l = [self.make_string(s) for s in self._str.rsplit(ch, max)]
        res = _array(Array(self._TYPE), len(l))
        res._array[:] = l
        return res

    def ll_contains(self, ch):
        # NOT_RPYTHON
        return ch in self._str

    def ll_replace_chr_chr(self, ch1, ch2):
        # NOT_RPYTHON
        return self.make_string(self._str.replace(ch1, ch2))

class _null_string(_null_mixin(_string), _string):
    def __init__(self, STRING):
        self.__dict__["_TYPE"] = STRING
        self.__dict__["_str"] = None

class _string_builder(_builtin_type):
    def __init__(self, STRING_BUILDER):
        self._TYPE = STRING_BUILDER
        self._buf = []

    def ll_allocate(self, n):
        assert isinstance(n, int)
        assert n >= 0
        # do nothing

    def ll_append_char(self, ch):
        assert isinstance(ch, basestring) and len(ch) == 1
        self._buf.append(ch)

    def ll_append(self, s):
        assert isinstance(s, _string)
        self._buf.append(s._str)

    def ll_build(self):
        if self._TYPE is StringBuilder:
            return make_string(''.join(self._buf))
        else:
            return make_unicode(u''.join(self._buf))

class _null_string_builder(_null_mixin(_string_builder), _string_builder):
    def __init__(self, STRING_BUILDER):
        self.__dict__["_TYPE"] = STRING_BUILDER

import weakref

class _weak_reference(_builtin_type):
    def __init__(self, WEAK_REFERENCE):
        self._TYPE = WEAK_REFERENCE
        self._ref = None

    def _unwrap_view(self, obj):
        # we can't store directly the view inside the weakref because
        # the view can be a temp object that is not referenced
        # anywhere else.
        while isinstance(obj, _view):
            obj = obj._inst
        return obj

    def ll_set(self, target):
        assert isinstance(typeOf(target), Instance)
        target = self._unwrap_view(target)
        self._ref = weakref.ref(target)

    def ll_deref(self):
        if self._ref is None:
            return null(ROOT)
        result = self._ref()
        if result is None:
            return null(ROOT)
        return _view(ROOT, result)

class _null_weak_reference(_null_mixin(_weak_reference), _weak_reference):
    def __init__(self, WEAK_REFERENCE):
        self.__dict__["_TYPE"] = WEAK_REFERENCE



class _list(_builtin_type):
    def __init__(self, LIST):
        self._TYPE = LIST
        self._list = []

    # The following are implementations of the abstract list interface for
    # use by the llinterpreter and ootype tests. There are NOT_RPYTHON
    # because the annotator is not supposed to follow them.

    def ll_length(self):
        # NOT_RPYTHON
        return len(self._list)

    def _ll_resize_ge(self, length):
        # NOT_RPYTHON        
        if len(self._list) < length:
            diff = length - len(self._list)
            self._list += [self._TYPE.ITEM._defl()] * diff
        assert len(self._list) >= length

    def _ll_resize_le(self, length):
        # NOT_RPYTHON
        if length < len(self._list):
            del self._list[length:]
        assert len(self._list) <= length

    def _ll_resize(self, length):
        # NOT_RPYTHON
        if length > len(self._list):
            self._ll_resize_ge(length)
        elif length < len(self._list):
            self._ll_resize_le(length)
        assert len(self._list) == length

    def ll_getitem_fast(self, index):
        # NOT_RPYTHON
        assert typeOf(index) == Signed
        assert index >= 0
        return self._list[index]

    def ll_setitem_fast(self, index, item):
        # NOT_RPYTHON
        assert self._TYPE.ITEM is Void or typeOf(item) == self._TYPE.ITEM
        assert typeOf(index) == Signed
        assert index >= 0
        self._list[index] = item

class _null_list(_null_mixin(_list), _list):

    def __init__(self, LIST):
        self.__dict__["_TYPE"] = LIST 

class _array(_builtin_type):
    def __init__(self, ARRAY, length):
        self._TYPE = ARRAY
        self._array = [ARRAY.ITEM._defl()] * length

    def ll_length(self):
        # NOT_RPYTHON
        return len(self._array)

    def ll_getitem_fast(self, index):
        # NOT_RPYTHON
        assert typeOf(index) == Signed
        assert index >= 0
        return self._array[index]

    def ll_setitem_fast(self, index, item):
        # NOT_RPYTHON
        assert self._TYPE.ITEM is Void or typeOf(item) == self._TYPE.ITEM
        assert typeOf(index) == Signed
        assert index >= 0
        self._array[index] = item

    def _identityhash(self):
        if self:
            return intmask(id(self))
        else:
            return 0 # for all null arrays

class _null_array(_null_mixin(_array), _array):

    def __init__(self, ARRAY):
        self.__dict__["_TYPE"] = ARRAY 

class _dict(_builtin_type):
    def __init__(self, DICT):
        self._TYPE = DICT
        self._dict = {}
        self._stamp = 0
        self._last_key = object() # placeholder != to everything else

    def ll_length(self):
        # NOT_RPYTHON
        return len(self._dict)

    def ll_get(self, key):
        # NOT_RPYTHON
        assert typeOf(key) == self._TYPE._KEYTYPE
        assert key in self._dict
        assert key == self._last_key
        return self._dict[key]

    def ll_set(self, key, value):
        # NOT_RPYTHON
        assert typeOf(key) == self._TYPE._KEYTYPE
        assert typeOf(value) == self._TYPE._VALUETYPE
        if key not in self._dict:
            self._stamp += 1
        self._dict[key] = value

    def ll_remove(self, key):
        # NOT_RPYTHON
        assert typeOf(key) == self._TYPE._KEYTYPE
        try:
            del self._dict[key]
            self._stamp += 1
            return True
        except KeyError:
            return False

    def ll_contains(self, key):
        # NOT_RPYTHON
        assert typeOf(key) == self._TYPE._KEYTYPE
        self._last_key = key
        return key in self._dict

    def ll_clear(self):
        self._dict.clear()
        self._stamp += 1

    def ll_get_items_iterator(self):
        # NOT_RPYTHON
        ITER = DictItemsIterator(self._TYPE._KEYTYPE, self._TYPE._VALUETYPE)
        iter = _dict_items_iterator(ITER)
        iter._set_dict(self)
        return iter

class _null_dict(_null_mixin(_dict), _dict):
    def __init__(self, DICT):
        self.__dict__["_TYPE"] = DICT

class _custom_dict(_dict):
    def __init__(self, DICT):
        self._TYPE = DICT
        self._stamp = 0
        self._dict = 'DICT_NOT_CREATED_YET' # it's created inside ll_set_functions

    def ll_set_functions(self, sm_eq, sm_hash):
        "NOT_RPYTHON"
        key_eq = sm_eq._callable
        key_hash = sm_hash._callable
        self._dict = objectmodel.r_dict(key_eq, key_hash)

    def ll_copy(self):
        "NOT_RPYTHON"
        res = self.__class__(self._TYPE)
        res._dict = self._dict.copy()
        return res

class _null_custom_dict(_null_mixin(_custom_dict), _custom_dict):
    def __init__(self, DICT):
        self.__dict__["_TYPE"] = DICT

class _dict_items_iterator(_builtin_type):
    def __init__(self, ITER):
        self._TYPE = ITER
        self._index = -1

    def _set_dict(self, d):
        self._dict = d
        self._items = d._dict.items()
        self._stamp = d._stamp

    def _check_stamp(self):
        if self._stamp != self._dict._stamp:
            raise RuntimeError, 'Dictionary changed during iteration'

    def ll_go_next(self):
        # NOT_RPYTHON
        self._check_stamp()
        self._index += 1        
        if self._index >= len(self._items):
            return False
        else:
            return True

    def ll_current_key(self):
        # NOT_RPYTHON
        self._check_stamp()
        assert 0 <= self._index < len(self._items)
        return self._items[self._index][0]
    
    def ll_current_value(self):
        # NOT_RPYTHON
        self._check_stamp()
        assert 0 <= self._index < len(self._items)
        return self._items[self._index][1]

class _null_dict_items_iterator(_null_mixin(_dict_items_iterator), _dict_items_iterator):
    def __init__(self, ITER):
        self.__dict__["_TYPE"] = ITER


class _record(object):

    def __init__(self, TYPE):
        self._items = {}
        self._TYPE = TYPE
        for name, (_, default) in TYPE._fields.items():
            self._items[name] = default

    def __getattr__(self, name):
        items = self.__dict__["_items"]
        if name in items:
            return items[name]
        return self.__dict__[name]

    def __setattr__(self, name, value):
        if hasattr(self, "_items") and name in self._items:
            self._items[name] = value
        else:
            self.__dict__[name] = value

    def _identityhash(self):
        if self:
            return intmask(id(self))
        else:
            return 0 # for all null records

    def _items_in_order(self):
        return [self._items[name] for name in self._TYPE._fields_in_order]

    def _ll_hash(self):
        return objectmodel._ll_hash_tuple(self._items_in_order())

    def __hash__(self):
        key = tuple(self._items_in_order())
        return hash(key)

    def __eq__(self, other):
        return self._TYPE == other._TYPE and self._items == other._items

    def __ne__(self, other):
        return not (self == other)

    def _cast_to_object(self):
        return make_object(self)

class _null_record(_null_mixin(_record), _record):

    def __init__(self, RECORD):
        self.__dict__["_TYPE"] = RECORD 


def new(TYPE):
    if isinstance(TYPE, Instance):
        return make_instance(TYPE)
    elif isinstance(TYPE, BuiltinType):
        return TYPE._get_interp_class()(TYPE)

def oonewcustomdict(DICT, ll_eq, ll_hash):
    """NOT_RPYTHON"""
    d = new(DICT)
    d.ll_set_functions(ll_eq, ll_hash)
    return d

def oonewarray(ARRAY, length):
    """NOT_RPYTHON"""
    return _array(ARRAY, length)

def runtimenew(class_):
    assert isinstance(class_, _class)
    assert class_ is not nullruntimeclass
    TYPE = class_._INSTANCE
    if isinstance(TYPE, Record):
        return _record(TYPE)
    else:
        return make_instance(TYPE)

def static_meth(FUNCTION, name,  **attrs):
    return _static_meth(FUNCTION, _name=name, **attrs)

def meth(METHOD, **attrs):
    return _meth(METHOD, **attrs)

def overload(*overloadings, **attrs):
    return _overloaded_meth(*overloadings, **attrs)

def null(INSTANCE_OR_FUNCTION):
    return INSTANCE_OR_FUNCTION._null

def instanceof(inst, INSTANCE):
    # this version of instanceof() accepts a NULL instance and always
    # returns False in this case.
    assert isinstance(typeOf(inst), Instance)
    return inst._instanceof(INSTANCE)

def classof(inst):
    assert isinstance(typeOf(inst), Instance)
    return inst._classof()

def dynamicType(inst):
    assert isinstance(typeOf(inst), Instance)
    return classof(inst)._INSTANCE

def subclassof(class1, class2):
    assert isinstance(class1, _class)
    assert isinstance(class2, _class)
    assert class1 is not nullruntimeclass
    assert class2 is not nullruntimeclass
    return isSubclass(class1._INSTANCE, class2._INSTANCE)

def addFields(INSTANCE, fields, with_default=False):
    INSTANCE._add_fields(fields, with_default)

def addMethods(INSTANCE, methods):
    INSTANCE._add_methods(methods)

def overrideDefaultForFields(INSTANCE, fields):
    INSTANCE._override_default_for_fields(fields)

def runtimeClass(TYPE):
    assert isinstance(TYPE, OOType)
    return TYPE._class

def isSubclass(C1, C2):
    c = C1
    while c is not None:
        if c == C2:
            return True
        c = c._superclass
    return False

def commonBaseclass(INSTANCE1, INSTANCE2):
    c = INSTANCE1
    while c is not None:
        if isSubclass(INSTANCE2, c):
            return c
        c = c._superclass
    return None

def ooupcast(INSTANCE, instance):
    return instance._upcast(INSTANCE)
    
def oodowncast(INSTANCE, instance):
    return instance._downcast(INSTANCE)

def cast_to_object(whatever):
    TYPE = typeOf(whatever)
    assert isinstance(TYPE, OOType)
    return whatever._cast_to_object()

def cast_from_object(EXPECTED_TYPE, obj):
    assert typeOf(obj) is Object
    return obj._cast_to(EXPECTED_TYPE)

class Box(_object):
    def __init__(self, i):
        self._TYPE = Object
        self.i = i

def oobox_int(i):
    return Box(i)
oobox_int.need_result_type = True

def oounbox_int(x):
    return x.i
oounbox_int.need_result_type = True

def oostring(obj, base):
    """
    Convert char, int, float, instances and str to str.
    
    Base is used only for formatting int: for other types is ignored
    and should be set to -1. For int only base 8, 10 and 16 are
    supported.
    """
    if isinstance(obj, int):
        assert base in (-1, 8, 10, 16)
        fmt = {-1:'%d', 8:'%o', 10:'%d', 16:'%x'}[base]
        obj = fmt % obj
    elif isinstance(obj, _view):
        obj = '<%s object>' % obj._inst._TYPE._name
    return make_string(str(obj))

def oounicode(obj, base):
    """
    Convert:
      - an unichar into an unicode string OR
      - a string into an unicode string

    base must be -1, for consistency with oostring.
    """
    assert base == -1
    if isinstance(obj, unicode):
        return make_unicode(obj)
    elif isinstance(obj, _string):
        s = unicode(obj._str)
        return make_unicode(s)
    else:
        assert False

def ooparse_int(s, base):
    return int(s._str, base)

def ooparse_float(s):
    return float(s._str)

def setItemType(LIST, ITEMTYPE):
    return LIST._set_itemtype(ITEMTYPE)

def hasItemType(LIST):
    return LIST.ITEM is not None

def setDictTypes(DICT, KEYTYPE, VALUETYPE):
    return DICT._set_types(KEYTYPE, VALUETYPE)

def setDictFunctions(DICT, ll_eq, ll_hash):
    return DICT._set_functions(ll_eq, ll_hash)

def hasDictTypes(DICT):
    return DICT._is_initialized()

def ooweakref_create(obj):
    ref = new(WeakReference)
    ref.ll_set(obj)
    return ref

def build_unbound_method_wrapper(meth):
    METH = typeOf(meth)
    methname = meth._name
    funcname = '%s_wrapper' % methname
    nb_args = len(METH.ARGS)
    arglist = ', '.join('a%d' % i for i in range(nb_args))
    ns = {'methname': methname}
    code = py.code.Source("""
    def %s(self, %s):
        m = getattr(self, methname)
        return m(%s)
    """ % (funcname, arglist, arglist))
    exec code.compile() in ns
    return ns[funcname]

Object = Object()
NULL = _object(None)
Object._null = NULL

ROOT = Instance('Root', None, _is_root=True)
String = String()
Unicode = Unicode()
UnicodeBuilder = StringBuilder(Unicode, UniChar)
StringBuilder = StringBuilder(String, Char)
String.builder = StringBuilder
Unicode.builder = UnicodeBuilder
WeakReference = WeakReference()
dead_wref = new(WeakReference)
