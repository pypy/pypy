from pypy.objspace.std.model import W_Object
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.function import Function, StaticMethod
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import weakref_descr
from pypy.objspace.std.stdtypedef import std_dict_descr, issubtypedef, Member
from pypy.objspace.std.objecttype import object_typedef
from pypy.objspace.std.dictproxyobject import W_DictProxyObject
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.objectmodel import current_object_addr_as_int, compute_hash
from pypy.rlib.jit import hint, purefunction_promote, we_are_jitted
from pypy.rlib.jit import purefunction, dont_look_inside, unroll_safe
from pypy.rlib.rarithmetic import intmask, r_uint

# from compiler/misc.py

MANGLE_LEN = 256 # magic constant from compile.c

def _mangle(name, klass):
    if not name.startswith('__'):
        return name
    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        end = len(klass) + MANGLE_LEN-tlen
        if end < 0:
            klass = ''     # annotator hint
        else:
            klass = klass[:end]

    return "_%s%s" % (klass, name)

class VersionTag(object):
    pass

class MethodCache(object):

    def __init__(self, space):
        assert space.config.objspace.std.withmethodcache
        SIZE = 1 << space.config.objspace.std.methodcachesizeexp
        self.versions = [None] * SIZE
        self.names = [None] * SIZE
        self.lookup_where = [(None, None)] * SIZE
        if space.config.objspace.std.withmethodcachecounter:
            self.hits = {}
            self.misses = {}

    def clear(self):
        None_None = (None, None)
        for i in range(len(self.versions)):
            self.versions[i] = None
        for i in range(len(self.names)):
            self.names[i] = None
        for i in range(len(self.lookup_where)):
            self.lookup_where[i] = None_None


class W_TypeObject(W_Object):
    from pypy.objspace.std.typetype import type_typedef as typedef

    lazyloaders = {} # can be overridden by specific instances

    # the version_tag changes if the dict or the inheritance hierarchy changes
    # other changes to the type (e.g. the name) leave it unchanged
    _version_tag = None

    _immutable_fields_ = ["flag_heaptype",
                          "flag_cpytype",
                          #  flag_abstract is not immutable
                          'needsdel',
                          'weakrefable',
                          'hasdict',
                          'nslots',
                          'instancetypedef',
                          'terminator',
                          ]

    # for config.objspace.std.getattributeshortcut
    # (False is a conservative default, fixed during real usage)
    uses_object_getattribute = False

    # used to cache the type __new__ function if it comes from a builtin type
    # != 'type', in that case call__Type will also assumes the result
    # of the __new__ is an instance of the type
    w_bltin_new = None

    @dont_look_inside
    def __init__(w_self, space, name, bases_w, dict_w,
                 overridetypedef=None):
        w_self.space = space
        w_self.name = name
        w_self.bases_w = bases_w
        w_self.dict_w = dict_w
        w_self.nslots = 0
        w_self.hasdict = False
        w_self.needsdel = False
        w_self.weakrefable = False
        w_self.w_doc = space.w_None
        w_self.weak_subclasses = []
        w_self.flag_heaptype = False
        w_self.flag_cpytype = False
        w_self.flag_abstract = False
        w_self.instancetypedef = overridetypedef

        if overridetypedef is not None:
            setup_builtin_type(w_self)
        else:
            setup_user_defined_type(w_self)
        w_self.w_same_layout_as = get_parent_layout(w_self)

        if space.config.objspace.std.withtypeversion:
            if not is_mro_purely_of_types(w_self.mro_w):
                pass
            else:
                # the _version_tag should change, whenever the content of
                # dict_w of any of the types in the mro changes, or if the mro
                # itself changes
                w_self._version_tag = VersionTag()
        if space.config.objspace.std.withmapdict:
            from pypy.objspace.std.mapdict import DictTerminator, NoDictTerminator
            if w_self.hasdict:
                w_self.terminator = DictTerminator(space, w_self)
            else:
                w_self.terminator = NoDictTerminator(space, w_self)

    def mutated(w_self):
        space = w_self.space
        assert w_self.is_heaptype() or space.config.objspace.std.mutable_builtintypes
        if (not space.config.objspace.std.withtypeversion and
            not space.config.objspace.std.getattributeshortcut and
            not space.config.objspace.std.newshortcut):
            return

        if space.config.objspace.std.getattributeshortcut:
            w_self.uses_object_getattribute = False
            # ^^^ conservative default, fixed during real usage

        if space.config.objspace.std.newshortcut:
            w_self.w_bltin_new = None

        if (space.config.objspace.std.withtypeversion
            and w_self._version_tag is not None):
            w_self._version_tag = VersionTag()

        subclasses_w = w_self.get_subclasses()
        for w_subclass in subclasses_w:
            assert isinstance(w_subclass, W_TypeObject)
            w_subclass.mutated()

    def version_tag(w_self):
        if (not we_are_jitted() or w_self.is_heaptype() or
            w_self.space.config.objspace.std.mutable_builtintypes):
            return w_self._version_tag
        # prebuilt objects cannot get their version_tag changed
        return w_self._pure_version_tag()

    @purefunction_promote()
    def _pure_version_tag(w_self):
        return w_self._version_tag

    def getattribute_if_not_from_object(w_self):
        """ this method returns the applevel __getattribute__ if that is not
        the one from object, in which case it returns None """
        from pypy.objspace.descroperation import object_getattribute
        if not we_are_jitted():
            shortcut = w_self.space.config.objspace.std.getattributeshortcut
            if not shortcut or not w_self.uses_object_getattribute:
                # slow path: look for a custom __getattribute__ on the class
                w_descr = w_self.lookup('__getattribute__')
                # if it was not actually overriden in the class, we remember this
                # fact for the next time.
                if w_descr is object_getattribute(w_self.space):
                    if shortcut:
                        w_self.uses_object_getattribute = True
                else:
                    return w_descr
            return None
        # in the JIT case, just use a lookup, because it is folded away
        # correctly using the version_tag
        w_descr = w_self.lookup('__getattribute__')
        if w_descr is not object_getattribute(w_self.space):
            return w_descr

    def has_object_getattribute(w_self):
        return w_self.getattribute_if_not_from_object() is None

    def ready(w_self):
        for w_base in w_self.bases_w:
            if not isinstance(w_base, W_TypeObject):
                continue
            w_base.add_subclass(w_self)

    # compute a tuple that fully describes the instance layout
    def get_full_instance_layout(w_self):
        w_layout = w_self.w_same_layout_as or w_self
        return (w_layout, w_self.hasdict, w_self.needsdel, w_self.weakrefable)

    def compute_default_mro(w_self):
        return compute_C3_mro(w_self.space, w_self)

    def getdictvalue(w_self, space, attr):
        w_value = w_self.dict_w.get(attr, None)
        if w_self.lazyloaders and w_value is None:
            if attr in w_self.lazyloaders:
                # very clever next line: it forces the attr string
                # to be interned.
                w_attr = space.new_interned_str(attr)
                loader = w_self.lazyloaders[attr]
                del w_self.lazyloaders[attr]
                w_value = loader()
                if w_value is not None:   # None means no such attribute
                    w_self.dict_w[attr] = w_value
                    return w_value
        return w_value

    def lookup(w_self, name):
        # note that this doesn't call __get__ on the result at all
        space = w_self.space
        if space.config.objspace.std.withmethodcache:
            return w_self.lookup_where_with_method_cache(name)[1]

        return w_self._lookup(name)

    def lookup_where(w_self, name):
        space = w_self.space
        if space.config.objspace.std.withmethodcache:
            return w_self.lookup_where_with_method_cache(name)

        return w_self._lookup_where(name)

    def lookup_starting_at(w_self, w_starttype, name):
        space = w_self.space
        # XXX Optimize this with method cache
        look = False
        for w_class in w_self.mro_w:
            if w_class is w_starttype:
                look = True
            elif look:
                w_value = w_class.getdictvalue(space, name)
                if w_value is not None:
                    return w_value
        return None
                
    @unroll_safe
    def _lookup(w_self, key):
        space = w_self.space
        for w_class in w_self.mro_w:
            w_value = w_class.getdictvalue(space, key)
            if w_value is not None:
                return w_value
        return None

    @unroll_safe
    def _lookup_where(w_self, key):
        # like lookup() but also returns the parent class in which the
        # attribute was found
        space = w_self.space
        for w_class in w_self.mro_w:
            w_value = w_class.getdictvalue(space, key)
            if w_value is not None:
                return w_class, w_value
        return None, None

    def _lookup_where_all_typeobjects(w_self, key):
        # like _lookup_where(), but when we know that w_self.mro_w only
        # contains W_TypeObjects.  (It differs from _lookup_where() mostly
        # from a JIT point of view: it cannot invoke arbitrary Python code.)
        space = w_self.space
        for w_class in w_self.mro_w:
            assert isinstance(w_class, W_TypeObject)
            w_value = w_class.getdictvalue(space, key)
            if w_value is not None:
                return w_class, w_value
        return None, None

    def lookup_where_with_method_cache(w_self, name):
        space = w_self.space
        w_self = hint(w_self, promote=True)
        assert space.config.objspace.std.withmethodcache
        version_tag = hint(w_self.version_tag(), promote=True)
        if version_tag is None:
            tup = w_self._lookup_where(name)
            return tup
        return w_self._pure_lookup_where_with_method_cache(name, version_tag)

    @purefunction
    def _pure_lookup_where_with_method_cache(w_self, name, version_tag):
        space = w_self.space
        cache = space.fromcache(MethodCache)
        SHIFT2 = r_uint.BITS - space.config.objspace.std.methodcachesizeexp
        SHIFT1 = SHIFT2 - 5
        version_tag_as_int = current_object_addr_as_int(version_tag)
        # ^^^Note: if the version_tag object is moved by a moving GC, the
        # existing method cache entries won't be found any more; new
        # entries will be created based on the new address.  The
        # assumption is that the version_tag object won't keep moving all
        # the time - so using the fast current_object_addr_as_int() instead
        # of a slower solution like hash() is still a good trade-off.
        hash_name = compute_hash(name)
        product = intmask(version_tag_as_int * hash_name)
        method_hash = (r_uint(product) ^ (r_uint(product) << SHIFT1)) >> SHIFT2
        # ^^^Note2: we used to just take product>>SHIFT2, but on 64-bit
        # platforms SHIFT2 is really large, and we loose too much information
        # that way (as shown by failures of the tests that typically have
        # method names like 'f' who hash to a number that has only ~33 bits).
        cached_version_tag = cache.versions[method_hash]
        if cached_version_tag is version_tag:
            cached_name = cache.names[method_hash]
            if cached_name is name:
                tup = cache.lookup_where[method_hash]
                if space.config.objspace.std.withmethodcachecounter:
                    cache.hits[name] = cache.hits.get(name, 0) + 1
#                print "hit", w_self, name
                return tup
        tup = w_self._lookup_where_all_typeobjects(name)
        cache.versions[method_hash] = version_tag
        cache.names[method_hash] = name
        cache.lookup_where[method_hash] = tup
        if space.config.objspace.std.withmethodcachecounter:
            cache.misses[name] = cache.misses.get(name, 0) + 1
#        print "miss", w_self, name
        return tup

    def check_user_subclass(w_self, w_subtype):
        space = w_self.space
        if not isinstance(w_subtype, W_TypeObject):
            raise operationerrfmt(space.w_TypeError,
                "X is not a type object ('%s')",
                space.type(w_subtype).getname(space))
        if not w_subtype.issubtype(w_self):
            raise operationerrfmt(space.w_TypeError,
                "%s.__new__(%s): %s is not a subtype of %s",
                w_self.name, w_subtype.name, w_subtype.name, w_self.name)
        if w_self.instancetypedef is not w_subtype.instancetypedef:
            raise operationerrfmt(space.w_TypeError,
                "%s.__new__(%s) is not safe, use %s.__new__()",
                w_self.name, w_subtype.name, w_subtype.name)
        return w_subtype

    def _freeze_(w_self):
        "NOT_RPYTHON.  Forces the lazy attributes to be computed."
        if 'lazyloaders' in w_self.__dict__:
            for attr in w_self.lazyloaders.keys():
                w_self.getdictvalue(w_self.space, attr)
            del w_self.lazyloaders
        return False

    def getdict(w_self, space): # returning a dict-proxy!
        if w_self.lazyloaders:
            w_self._freeze_()    # force un-lazification
        newdic = space.newdict(from_strdict_shared=w_self.dict_w)
        return W_DictProxyObject(newdic)

    def unwrap(w_self, space):
        if w_self.instancetypedef.fakedcpytype is not None:
            return w_self.instancetypedef.fakedcpytype
        from pypy.objspace.std.model import UnwrapError
        raise UnwrapError(w_self)

    def is_heaptype(w_self):
        return w_self.flag_heaptype

    def is_cpytype(w_self):
        return w_self.flag_cpytype

    def is_abstract(w_self):
        return w_self.flag_abstract

    def set_abstract(w_self, abstract):
        w_self.flag_abstract = bool(abstract)

    def issubtype(w_self, w_type):
        w_self = hint(w_self, promote=True)
        w_type = hint(w_type, promote=True)
        if w_self.space.config.objspace.std.withtypeversion and we_are_jitted():
            version_tag1 = w_self.version_tag()
            version_tag2 = w_type.version_tag()
            if version_tag1 is not None and version_tag2 is not None:
                res = _pure_issubtype(w_self, w_type, version_tag1, version_tag2)
                return res
        return _issubtype(w_self, w_type)

    def get_module(w_self):
        space = w_self.space
        if w_self.is_heaptype() and '__module__' in w_self.dict_w:
            return w_self.dict_w['__module__']
        else:
            # for non-heap types, CPython checks for a module.name in the
            # type name.  That's a hack, so we're allowed to use a different
            # hack...
            if ('__module__' in w_self.dict_w and
                space.is_true(space.isinstance(w_self.dict_w['__module__'],
                                               space.w_str))):
                return w_self.dict_w['__module__']
            return space.wrap('__builtin__')

    def get_module_type_name(w_self):
        space = w_self.space
        w_mod = w_self.get_module()
        if not space.is_true(space.isinstance(w_mod, space.w_str)):
            mod = '__builtin__'
        else:
            mod = space.str_w(w_mod)
        if mod !='__builtin__':
            return '%s.%s' % (mod, w_self.name)
        else:
            return w_self.name

    def add_subclass(w_self, w_subclass):
        space = w_self.space
        if not space.config.translation.rweakref:
            return    # no weakref support, don't keep track of subclasses
        import weakref
        assert isinstance(w_subclass, W_TypeObject)
        newref = weakref.ref(w_subclass)
        for i in range(len(w_self.weak_subclasses)):
            ref = w_self.weak_subclasses[i]
            if ref() is None:
                w_self.weak_subclasses[i] = newref
                return
        else:
            w_self.weak_subclasses.append(newref)

    def remove_subclass(w_self, w_subclass):
        space = w_self.space
        if not space.config.translation.rweakref:
            return    # no weakref support, don't keep track of subclasses
        for i in range(len(w_self.weak_subclasses)):
            ref = w_self.weak_subclasses[i]
            if ref() is w_subclass:
                del w_self.weak_subclasses[i]
                return

    def get_subclasses(w_self):
        space = w_self.space
        if not space.config.translation.rweakref:
            msg = ("this feature requires weakrefs, "
                   "which are not available in this build of PyPy")
            raise OperationError(space.w_RuntimeError,
                                 space.wrap(msg))
        subclasses_w = []
        for ref in w_self.weak_subclasses:
            w_ob = ref()
            if w_ob is not None:
                subclasses_w.append(w_ob)
        return subclasses_w


    # for now, weakref support for W_TypeObject is hard to get automatically
    _lifeline_ = None
    def getweakref(self):
        return self._lifeline_
    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline

# ____________________________________________________________
# Initialization of type objects

def get_parent_layout(w_type):
    """Compute the most parent class of 'w_type' whose layout
       is the same as 'w_type', or None if all parents of 'w_type'
       have a different layout than 'w_type'.
    """
    w_starttype = w_type
    while len(w_type.bases_w) > 0:
        w_bestbase = find_best_base(w_type.space, w_type.bases_w)
        if w_type.instancetypedef is not w_bestbase.instancetypedef:
            break
        if w_type.nslots != w_bestbase.nslots:
            break
        w_type = w_bestbase
    if w_type is not w_starttype:
        return w_type
    else:
        return None

def issublayout(w_layout1, w_layout2):
    space = w_layout2.space
    while w_layout1 is not w_layout2:
        w_layout1 = find_best_base(space, w_layout1.bases_w)
        if w_layout1 is None:
            return False
        w_layout1 = w_layout1.w_same_layout_as or w_layout1
    return True

def find_best_base(space, bases_w):
    """The best base is one of the bases in the given list: the one
       whose layout a new type should use as a starting point.
    """
    w_bestbase = None
    for w_candidate in bases_w:
        if not isinstance(w_candidate, W_TypeObject):
            continue
        if w_bestbase is None:
            w_bestbase = w_candidate   # for now
            continue
        candtypedef = w_candidate.instancetypedef
        besttypedef = w_bestbase.instancetypedef
        if candtypedef is besttypedef:
            # two candidates with the same typedef are equivalent unless
            # one has extra slots over the other
            if w_candidate.nslots > w_bestbase.nslots:
                w_bestbase = w_candidate
        elif issubtypedef(candtypedef, besttypedef):
            w_bestbase = w_candidate
    return w_bestbase

def check_and_find_best_base(space, bases_w):
    """The best base is one of the bases in the given list: the one
       whose layout a new type should use as a starting point.
       This version checks that bases_w is an acceptable tuple of bases.
    """
    w_bestbase = find_best_base(space, bases_w)
    if w_bestbase is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("a new-style class can't have "
                                        "only classic bases"))
    if not w_bestbase.instancetypedef.acceptable_as_base_class:
        raise operationerrfmt(space.w_TypeError,
                              "type '%s' is not an "
                              "acceptable base class",
                              w_bestbase.instancetypedef.name)

    # check that all other bases' layouts are superclasses of the bestbase
    w_bestlayout = w_bestbase.w_same_layout_as or w_bestbase
    for w_base in bases_w:
        if isinstance(w_base, W_TypeObject):
            w_layout = w_base.w_same_layout_as or w_base
            if not issublayout(w_bestlayout, w_layout):
                raise OperationError(space.w_TypeError,
                                     space.wrap("instance layout conflicts in "
                                                "multiple inheritance"))
    return w_bestbase

def copy_flags_from_bases(w_self, w_bestbase):
    hasoldstylebase = False
    for w_base in w_self.bases_w:
        if not isinstance(w_base, W_TypeObject):
            hasoldstylebase = True
            continue
        w_self.hasdict = w_self.hasdict or w_base.hasdict
        w_self.needsdel = w_self.needsdel or w_base.needsdel
        w_self.weakrefable = w_self.weakrefable or w_base.weakrefable
    w_self.nslots = w_bestbase.nslots
    return hasoldstylebase

def create_all_slots(w_self, hasoldstylebase):
    space = w_self.space
    dict_w = w_self.dict_w
    if '__slots__' not in dict_w:
        wantdict = True
        wantweakref = True
    else:
        wantdict = False
        wantweakref = False
        w_slots = dict_w['__slots__']
        if (space.isinstance_w(w_slots, space.w_str) or
            space.isinstance_w(w_slots, space.w_unicode)):
            slot_names_w = [w_slots]
        else:
            slot_names_w = space.unpackiterable(w_slots)
        for w_slot_name in slot_names_w:
            slot_name = space.str_w(w_slot_name)
            if slot_name == '__dict__':
                if wantdict or w_self.hasdict:
                    raise OperationError(space.w_TypeError,
                            space.wrap("__dict__ slot disallowed: "
                                       "we already got one"))
                wantdict = True
            elif slot_name == '__weakref__':
                if wantweakref or w_self.weakrefable:
                    raise OperationError(space.w_TypeError,
                            space.wrap("__weakref__ slot disallowed: "
                                       "we already got one"))
                wantweakref = True
            else:
                create_slot(w_self, slot_name)
    wantdict = wantdict or hasoldstylebase
    if wantdict: create_dict_slot(w_self)
    if wantweakref: create_weakref_slot(w_self)
    if '__del__' in dict_w: w_self.needsdel = True

def create_slot(w_self, slot_name):
    space = w_self.space
    if not valid_slot_name(slot_name):
        raise OperationError(space.w_TypeError,
                             space.wrap('__slots__ must be identifiers'))
    # create member
    slot_name = _mangle(slot_name, w_self.name)
    if slot_name not in w_self.dict_w:
        # Force interning of slot names.
        slot_name = space.str_w(space.new_interned_str(slot_name))
        # in cpython it is ignored less, but we probably don't care
        member = Member(w_self.nslots, slot_name, w_self)
        w_self.dict_w[slot_name] = space.wrap(member)
        w_self.nslots += 1

def create_dict_slot(w_self):
    if not w_self.hasdict:
        w_self.dict_w.setdefault('__dict__',
                                 w_self.space.wrap(std_dict_descr))
        w_self.hasdict = True

def create_weakref_slot(w_self):
    if not w_self.weakrefable:
        w_self.dict_w.setdefault('__weakref__',
                                 w_self.space.wrap(weakref_descr))
        w_self.weakrefable = True

def valid_slot_name(slot_name):
    if len(slot_name) == 0 or slot_name[0].isdigit():
        return False
    for c in slot_name:
        if not c.isalnum() and c != '_':
            return False
    return True

def setup_user_defined_type(w_self):
    if len(w_self.bases_w) == 0:
        w_self.bases_w = [w_self.space.w_object]
    w_bestbase = check_and_find_best_base(w_self.space, w_self.bases_w)
    w_self.instancetypedef = w_bestbase.instancetypedef
    w_self.flag_heaptype = True
    for w_base in w_self.bases_w:
        if not isinstance(w_base, W_TypeObject):
            continue
        w_self.flag_cpytype |= w_base.flag_cpytype
        w_self.flag_abstract |= w_base.flag_abstract

    hasoldstylebase = copy_flags_from_bases(w_self, w_bestbase)
    create_all_slots(w_self, hasoldstylebase)

    ensure_common_attributes(w_self)

def setup_builtin_type(w_self):
    w_self.hasdict = w_self.instancetypedef.hasdict
    w_self.weakrefable = w_self.instancetypedef.weakrefable
    w_self.w_doc = w_self.space.wrap(w_self.instancetypedef.doc)
    ensure_common_attributes(w_self)

def ensure_common_attributes(w_self):
    ensure_static_new(w_self)
    w_self.dict_w.setdefault('__doc__', w_self.w_doc)
    if w_self.is_heaptype():
        ensure_module_attr(w_self)
    w_self.mro_w = []      # temporarily
    compute_mro(w_self)

def ensure_static_new(w_self):
    # special-case __new__, as in CPython:
    # if it is a Function, turn it into a static method
    if '__new__' in w_self.dict_w:
        w_new = w_self.dict_w['__new__']
        if isinstance(w_new, Function):
            w_self.dict_w['__new__'] = StaticMethod(w_new)

def ensure_module_attr(w_self):
    # initialize __module__ in the dict (user-defined types only)
    if '__module__' not in w_self.dict_w:
        space = w_self.space
        caller = space.getexecutioncontext().gettopframe_nohidden()
        if caller is not None:
            w_globals = caller.w_globals
            w_name = space.finditem(w_globals, space.wrap('__name__'))
            if w_name is not None:
                w_self.dict_w['__module__'] = w_name

def compute_mro(w_self):
    if w_self.is_heaptype():
        space = w_self.space
        w_metaclass = space.type(w_self)
        w_where, w_mro_func = space.lookup_in_type_where(w_metaclass, 'mro')
        if w_mro_func is not None and not space.is_w(w_where, space.w_type):
            w_mro_meth = space.get(w_mro_func, w_self)
            w_mro = space.call_function(w_mro_meth)
            mro_w = space.fixedview(w_mro)
            w_self.mro_w = validate_custom_mro(space, mro_w)
            return    # done
    w_self.mro_w = w_self.compute_default_mro()[:]

def validate_custom_mro(space, mro_w):
    # do some checking here.  Note that unlike CPython, strange MROs
    # cannot really segfault PyPy.  At a minimum, we check that all
    # the elements in the mro seem to be (old- or new-style) classes.
    for w_class in mro_w:
        if not space.abstract_isclass_w(w_class):
            raise OperationError(space.w_TypeError,
                                 space.wrap("mro() returned a non-class"))
    return mro_w

def is_mro_purely_of_types(mro_w):
    for w_class in mro_w:
        if not isinstance(w_class, W_TypeObject):
            return False
    return True

# ____________________________________________________________

def call__Type(space, w_type, __args__):
    w_type = hint(w_type, promote=True)
    # special case for type(x)
    if space.is_w(w_type, space.w_type):
        try:
            w_obj, = __args__.fixedunpack(1)
        except ValueError:
            pass
        else:
            return space.type(w_obj)
    # invoke the __new__ of the type
    if not we_are_jitted():
        # note that the annotator will figure out that w_type.w_bltin_new can
        # only be None if the newshortcut config option is not set
        w_bltin_new = w_type.w_bltin_new
    else:
        # for the JIT it is better to take the slow path because normal lookup
        # is nicely optimized, but the w_type.w_bltin_new attribute is not
        # known to the JIT
        w_bltin_new = None
    call_init = True
    if w_bltin_new is not None:
        w_newobject = space.call_obj_args(w_bltin_new, w_type, __args__)
    else:
        w_newtype, w_newdescr = w_type.lookup_where('__new__')
        w_newfunc = space.get(w_newdescr, w_type)
        if (space.config.objspace.std.newshortcut and
            not we_are_jitted() and
            isinstance(w_newtype, W_TypeObject) and
            not w_newtype.is_heaptype() and
            not space.is_w(w_newtype, space.w_type)):
            w_type.w_bltin_new = w_newfunc
        w_newobject = space.call_obj_args(w_newfunc, w_type, __args__)
        call_init = space.is_true(space.isinstance(w_newobject, w_type))

    # maybe invoke the __init__ of the type
    if call_init:
        w_descr = space.lookup(w_newobject, '__init__')
        w_result = space.get_and_call_args(w_descr, w_newobject, __args__)
        if not space.is_w(w_result, space.w_None):
            raise OperationError(space.w_TypeError,
                                 space.wrap("__init__() should return None"))
    return w_newobject

def _issubtype(w_sub, w_type):
    return w_type in w_sub.mro_w

@purefunction_promote()
def _pure_issubtype(w_sub, w_type, version_tag1, version_tag2):
    return _issubtype(w_sub, w_type)

def issubtype__Type_Type(space, w_type, w_sub):
    return space.newbool(w_sub.issubtype(w_type))

def isinstance__Type_ANY(space, w_type, w_inst):
    return space.newbool(space.type(w_inst).issubtype(w_type))

def repr__Type(space, w_obj):
    w_mod = w_obj.get_module()
    if not space.is_true(space.isinstance(w_mod, space.w_str)):
        mod = None
    else:
        mod = space.str_w(w_mod)
    if (not w_obj.is_heaptype() or
        (mod == '__builtin__' or mod == 'exceptions')):
        kind = 'type'
    else:
        kind = 'class'
    if mod is not None and mod !='__builtin__':
        return space.wrap("<%s '%s.%s'>" % (kind, mod, w_obj.name))
    else:
        return space.wrap("<%s '%s'>" % (kind, w_obj.name))

def getattr__Type_ANY(space, w_type, w_name):
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            w_get = space.lookup(w_descr, "__get__")
            if w_get is not None:
                return space.get_and_call_function(w_get, w_descr, w_type,
                                                   space.type(w_type))
    w_value = w_type.lookup(name)
    if w_value is not None:
        # __get__(None, type): turns e.g. functions into unbound methods
        return space.get(w_value, space.w_None, w_type)
    if w_descr is not None:
        return space.get(w_descr,w_type)
    raise operationerrfmt(space.w_AttributeError,
                          "type object '%s' has no attribute '%s'",
                          w_type.name, name)

def setattr__Type_ANY_ANY(space, w_type, w_name, w_value):
    # Note. This is exactly the same thing as descroperation.descr__setattr__,
    # but it is needed at bootstrap to avoid a call to w_type.getdict() which
    # would un-lazify the whole type.
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            space.set(w_descr, w_type, w_value)
            return
    
    if (not space.config.objspace.std.mutable_builtintypes
            and not w_type.is_heaptype()):
        msg = "can't set attributes on type object '%s'"
        raise operationerrfmt(space.w_TypeError, msg, w_type.name)
    if name == "__del__" and name not in w_type.dict_w:
        msg = "a __del__ method added to an existing type will not be called"
        space.warn(msg, space.w_RuntimeWarning)
    w_type.mutated()
    w_type.dict_w[name] = w_value

def eq__Type_Type(space, w_self, w_other):
    return space.is_(w_self, w_other)

def delattr__Type_ANY(space, w_type, w_name):
    if w_type.lazyloaders:
        w_type._freeze_()    # force un-lazification
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            space.delete(w_descr, w_type)
            return
    if (not space.config.objspace.std.mutable_builtintypes
            and not w_type.is_heaptype()):
        msg = "can't delete attributes on type object '%s'"
        raise operationerrfmt(space.w_TypeError, msg, w_type.name)
    try:
        del w_type.dict_w[name]
    except KeyError:
        raise OperationError(space.w_AttributeError, w_name)
    else:
        w_type.mutated()
        return


# ____________________________________________________________


abstract_mro = gateway.applevel("""
    def abstract_mro(klass):
        # abstract/classic mro
        mro = []
        stack = [klass]
        while stack:
            klass = stack.pop()
            if klass not in mro:
                mro.append(klass)
                if not isinstance(klass.__bases__, tuple):
                    raise TypeError, '__bases__ must be a tuple'
                stack += klass.__bases__[::-1]
        return mro
""", filename=__file__).interphook("abstract_mro")

def get_mro(space, klass):
    if isinstance(klass, W_TypeObject):
        return list(klass.mro_w)
    else:
        return space.unpackiterable(abstract_mro(space, klass))


def compute_C3_mro(space, cls):
    order = []
    orderlists = [get_mro(space, base) for base in cls.bases_w]
    orderlists.append([cls] + cls.bases_w)
    while orderlists:
        for candidatelist in orderlists:
            candidate = candidatelist[0]
            if mro_blockinglist(candidate, orderlists) is None:
                break    # good candidate
        else:
            return mro_error(space, orderlists)  # no candidate found
        assert candidate not in order
        order.append(candidate)
        for i in range(len(orderlists)-1, -1, -1):
            if orderlists[i][0] is candidate:
                del orderlists[i][0]
                if len(orderlists[i]) == 0:
                    del orderlists[i]
    return order


def mro_blockinglist(candidate, orderlists):
    for lst in orderlists:
        if candidate in lst[1:]:
            return lst
    return None # good candidate

def mro_error(space, orderlists):
    cycle = []
    candidate = orderlists[-1][0]
    if candidate in orderlists[-1][1:]:
        # explicit error message for this specific case
        raise operationerrfmt(space.w_TypeError,
                              "duplicate base class '%s'",
                              candidate.getname(space))
    while candidate not in cycle:
        cycle.append(candidate)
        nextblockinglist = mro_blockinglist(candidate, orderlists)
        candidate = nextblockinglist[0]
    del cycle[:cycle.index(candidate)]
    cycle.append(candidate)
    cycle.reverse()
    names = [cls.getname(space) for cls in cycle]
    raise OperationError(space.w_TypeError,
        space.wrap("cycle among base classes: " + ' < '.join(names)))

# ____________________________________________________________

register_all(vars())
