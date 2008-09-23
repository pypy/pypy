import types
from pypy.annotation import model as annmodel
#from pypy.annotation.classdef import isclassdef
from pypy.annotation import description
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, getgcflavor

def getclassrepr(rtyper, classdef):
    try:
        result = rtyper.class_reprs[classdef]
    except KeyError:
        result = rtyper.type_system.rclass.ClassRepr(rtyper, classdef)
        rtyper.class_reprs[classdef] = result
        rtyper.add_pendingsetup(result)
    return result

def getinstancerepr(rtyper, classdef, default_flavor='gc'):
    if classdef is None:
        flavor = default_flavor
    else:
        flavor = getgcflavor(classdef)
    try:
        result = rtyper.instance_reprs[classdef, flavor]
    except KeyError:
        result = rtyper.type_system.rclass.buildinstancerepr(
                        rtyper, classdef, gcflavor=flavor)

        rtyper.instance_reprs[classdef, flavor] = result
        rtyper.add_pendingsetup(result)
    return result

class MissingRTypeAttribute(TyperError):
    pass

class AbstractClassRepr(Repr):
    def __init__(self, rtyper, classdef):
        self.rtyper = rtyper
        self.classdef = classdef

    def _setup_repr(self):
        pass

    def __repr__(self):
        if self.classdef is None:
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return '<ClassRepr for %s>' % (clsname,)

    def compact_repr(self):
        if self.classdef is None:
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return 'ClassR %s' % (clsname,)

    def convert_desc(self, desc):
        subclassdef = desc.getuniqueclassdef()
        if self.classdef is not None:
            if self.classdef.commonbase(subclassdef) != self.classdef:
                raise TyperError("not a subclass of %r: %r" % (
                    self.classdef.name, desc))
        
        r_subclass = getclassrepr(self.rtyper, subclassdef)
        return r_subclass.getruntime(self.lowleveltype)

    def convert_const(self, value):
        if not isinstance(value, (type, types.ClassType)):
            raise TyperError("not a class: %r" % (value,))
        bk = self.rtyper.annotator.bookkeeper
        return self.convert_desc(bk.getdesc(value))

    def prepare_method(self, s_value):
        # special-casing for methods:
        #  if s_value is SomePBC([MethodDescs...])
        #  return a PBC representing the underlying functions
        if isinstance(s_value, annmodel.SomePBC):
            if not s_value.isNone() and s_value.getKind() == description.MethodDesc:
                s_value = self.classdef.lookup_filter(s_value)
                funcdescs = [mdesc.funcdesc for mdesc in s_value.descriptions]
                return annmodel.SomePBC(funcdescs)
        return None   # not a method

    def get_ll_eq_function(self):
        return None

def get_type_repr(rtyper):
    return getclassrepr(rtyper, None)

# ____________________________________________________________


class __extend__(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return getinstancerepr(rtyper, self.classdef)
    def rtyper_makekey(self):
        return self.__class__, self.classdef


class AbstractInstanceRepr(Repr):
    def __init__(self, rtyper, classdef):
        self.rtyper = rtyper
        self.classdef = classdef

    def _setup_repr(self):
        pass

    def __repr__(self):
        if self.classdef is None:
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return '<InstanceRepr for %s>' % (clsname,)

    def compact_repr(self):
        if self.classdef is None:
            clsname = 'object'
        else:
            clsname = self.classdef.name
        return 'InstanceR %s' % (clsname,)

    def _setup_repr_final(self):
        pass

    def new_instance(self, llops, classcallhop=None):
        raise NotImplementedError

    def convert_const(self, value):
        if value is None:
            return self.null_instance()
        if isinstance(value, types.MethodType):
            value = value.im_self   # bound method -> instance
        bk = self.rtyper.annotator.bookkeeper
        try:
            classdef = bk.getuniqueclassdef(value.__class__)
        except KeyError:
            raise TyperError("no classdef: %r" % (value.__class__,))
        if classdef != self.classdef:
            # if the class does not match exactly, check that 'value' is an
            # instance of a subclass and delegate to that InstanceRepr
            if classdef.commonbase(self.classdef) != self.classdef:
                raise TyperError("not an instance of %r: %r" % (
                    self.classdef.name, value))
            rinstance = getinstancerepr(self.rtyper, classdef)
            result = rinstance.convert_const(value)
            return self.upcast(result)
        # common case
        return self.convert_const_exact(value)

    def convert_const_exact(self, value):
        try:
            return self.prebuiltinstances[id(value)][1]
        except KeyError:
            self.setup()
            result = self.create_instance()
            self.prebuiltinstances[id(value)] = value, result
            self.initialize_prebuilt_instance(value, self.classdef, result)
            return result

    def get_reusable_prebuilt_instance(self):
        "Get a dummy prebuilt instance.  Multiple calls reuse the same one."
        try:
            return self._reusable_prebuilt_instance
        except AttributeError:
            self.setup()
            result = self.create_instance()
            self._reusable_prebuilt_instance = result
            self.initialize_prebuilt_instance(Ellipsis, self.classdef, result)
            return result

    def initialize_prebuilt_instance(self, value, classdef, result):
        # must fill in the _hash_cache_ field before the other ones
        # (see test_circular_hash_initialization)
        self.initialize_prebuilt_hash(value, result)
        self.initialize_prebuilt_data(value, classdef, result)

    def rtype_type(self, hop):
        raise NotImplementedError

    def rtype_getattr(self, hop):
        raise NotImplementedError

    def rtype_setattr(self, hop):
        raise NotImplementedError

    def rtype_is_true(self, hop):
        raise NotImplementedError

    def ll_str(self, i):
        raise NotImplementedError

    def get_ll_eq_function(self):
        return None    # defaults to compare by identity ('==' on pointers)

    def can_ll_be_null(self, s_value):
        return s_value.can_be_none()

# ____________________________________________________________

def rtype_new_instance(rtyper, classdef, llops, classcallhop=None):
    rinstance = getinstancerepr(rtyper, classdef)
    return rinstance.new_instance(llops, classcallhop)


_missing = object()

def fishllattr(inst, name, default=_missing):
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython.ootypesystem import ootype
    if isinstance(inst, (ootype._instance, ootype._view)):
        # XXX: we need to call ootypesystem.rclass.mangle, but we
        # can't because we don't have a config object
        mangled = 'o' + name
        if default is _missing:
            return getattr(inst, mangled)
        else:
            return getattr(inst, mangled, default)
    else:
        p = widest = lltype.normalizeptr(inst)
        while True:
            try:
                return getattr(p, 'inst_' + name)
            except AttributeError:
                pass
            try:
                p = p.super
            except AttributeError:
                break
        if default is _missing:
            raise AttributeError("%s has no field %s" % (lltype.typeOf(widest),
                                                         name))
        return default
