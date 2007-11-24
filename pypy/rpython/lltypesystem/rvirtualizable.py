from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem.rclass import OBJECTPTR, InstanceRepr
from pypy.rpython.annlowlevel import cachedtype

VABLERTIPTR = OBJECTPTR

class VirtualizableInstanceRepr(InstanceRepr):

    def __init__(self, rtyper, classdef):
        InstanceRepr.__init__(self, rtyper, classdef)
        classdesc = classdef.classdesc
        if '_virtualizable_' in classdesc.classdict:
            basedesc = classdesc.basedesc
            assert basedesc is None or basedesc.lookup('_virtualizable_') is None
            self.top_of_virtualizable_hierarchy = True
        else:
            self.top_of_virtualizable_hierarchy = False
        self._setters = {}
        self._getters = {}


    def _setup_repr(self):
        llfields = []
        ACCESS = lltype.ForwardReference()
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_base',   llmemory.Address))
            llfields.append(('vable_rti',   VABLERTIPTR))
            llfields.append(('vable_access', lltype.Ptr(ACCESS)))
        InstanceRepr._setup_repr(self, llfields,
                                 hints = {'virtualizable': True},
                                 adtmeths = {'ACCESS': ACCESS})
        rbase = self.rbase
        accessors = []
        if self.top_of_virtualizable_hierarchy:
            if len(rbase.allinstancefields) != 1:
                raise TyperError("virtulizable class cannot have"
                                 " non-virtualizable base class with instance"
                                 " fields: %r" % self.classdef)
            redirected_fields = []

        else:
            accessors.append(('parent', rbase.ACCESS))
            redirected_fields = list(rbase.ACCESS.redirected_fields)
        name = self.lowleveltype.TO._name
        TOPPTR = self.get_top_virtualizable_type()
        self.my_redirected_fields = my_redirected_fields = {}
        for name, (mangled_name, r) in self.fields.items():
            T = r.lowleveltype
            if T is lltype.Void:
                continue
            GETTER = lltype.Ptr(lltype.FuncType([TOPPTR], T))
            SETTER = lltype.Ptr(lltype.FuncType([TOPPTR, T], lltype.Void))
            accessors.append(('get_'+mangled_name, GETTER))
            accessors.append(('set_'+mangled_name, SETTER))
            redirected_fields.append(mangled_name)
            my_redirected_fields[name] = None
        ACCESS.become(lltype.Struct(name+'_access',
                                    hints = {'immutable': True},
                                    adtmeths = {'redirected_fields': tuple(redirected_fields)},
                                    *accessors))
                                    
        self.ACCESS = ACCESS

    def get_top_virtualizable_type(self):
        if self.top_of_virtualizable_hierarchy:
            return self.lowleveltype
        else:
            return self.rbase.get_top_virtualizable_type()

    def set_vable(self, llops, vinst, force_cast=False):
        if self.top_of_virtualizable_hierarchy:
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            for name, llvalue in (('access', lltype.nullptr(self.ACCESS)),
                                  ('base',   llmemory.NULL),
                                  ('rti',    lltype.nullptr(VABLERTIPTR.TO))):
                cname = inputconst(lltype.Void, 'vable_'+name)
                vvalue = inputconst(lltype.typeOf(llvalue), llvalue)
                llops.genop('setfield', [vinst, cname, vvalue])
        else:
            self.rbase.set_vable(llops, vinst, force_cast=True)

    def new_instance(self, llops, classcallhop=None):
        vptr = InstanceRepr.new_instance(self, llops, classcallhop)
        self.set_vable(llops, vptr)
        return vptr

    def get_getter(self, name):
        try:
            return self._getters[name]
        except KeyError:
            pass
        TOPPTR = self.get_top_virtualizable_type()
        ACCESSPTR =  lltype.Ptr(self.ACCESS)
        def ll_getter(inst):
            top = lltype.cast_pointer(TOPPTR, inst)
            access = top.vable_access
            if access:
                return getattr(lltype.cast_pointer(ACCESSPTR, access),
                               'get_'+name)(top)
            else:
                return getattr(inst, name)
        ll_getter.oopspec = 'vable.get_%s(inst)' % name
        self._getters[name] = ll_getter
        return ll_getter

    def get_setter(self, name):
        try:
            return self._setters[name]
        except KeyError:
            pass
        TOPPTR = self.get_top_virtualizable_type()
        ACCESSPTR =  lltype.Ptr(self.ACCESS)
        def ll_setter(inst, value):
            top = lltype.cast_pointer(TOPPTR, inst)
            access = top.vable_access
            if access:
                return getattr(lltype.cast_pointer(ACCESSPTR, access),
                               'set_'+name)(top, value)
            else:
                return setattr(inst, name, value)
        ll_setter.oopspec = 'vable.set_%s(inst, value)' % name
        self._setters[name] = ll_setter
        return ll_setter
   

    def getfield(self, vinst, attr, llops, force_cast=False, flags={}):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if (attr in self.my_redirected_fields
            and not flags.get('access_directly')):
            mangled_name, r = self.fields[attr]
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            ll_getter = self.get_getter(mangled_name)
            return llops.gendirectcall(ll_getter, vinst)
        else:
            return InstanceRepr.getfield(self, vinst, attr, llops, force_cast)

    def setfield(self, vinst, attr, vvalue, llops, force_cast=False,
                 flags={}):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if (attr in self.my_redirected_fields
            and not flags.get('access_directly')):
            mangled_name, r = self.fields[attr]
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            ll_setter = self.get_setter(mangled_name)                
            llops.gendirectcall(ll_setter, vinst, vvalue)
        else:
            InstanceRepr.setfield(self, vinst, attr, vvalue, llops, force_cast)
