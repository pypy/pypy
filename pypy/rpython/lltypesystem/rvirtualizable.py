from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem.rclass import InstanceRepr
from pypy.rpython.annlowlevel import cachedtype

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


    def _setup_repr(self):
        llfields = []
        ACCESS = lltype.ForwardReference()
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_access', lltype.Ptr(ACCESS)))
        InstanceRepr._setup_repr(self, llfields,
                                 adtmeths={'ACCESS': ACCESS})
        rbase = self.rbase
        accessors = []
        if self.top_of_virtualizable_hierarchy:
            if len(rbase.allinstancefields) != 1:
                raise TyperError("virtulizable class cannot have"
                                 " non-virtualizable base class with instance"
                                 " fields: %r" % self.classdef)
        else:
            accessors.append(('parent', rbase.ACCESS))
        name = self.lowleveltype.TO._name
        SELF = self.lowleveltype
        for name, (mangled_name, r) in self.fields.items():
            T = r.lowleveltype
            GETTER = lltype.Ptr(lltype.FuncType([SELF], T))
            SETTER = lltype.Ptr(lltype.FuncType([SELF, T], lltype.Void))
            accessors.append(('get_'+mangled_name, GETTER))
            accessors.append(('set_'+mangled_name, SETTER))
        ACCESS.become(lltype.Struct(name+'_access', *accessors))
                                    
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
            for name, llvalue in (('access', lltype.nullptr(self.ACCESS)),):
                cname = inputconst(lltype.Void, 'vable_'+name)
                vvalue = inputconst(lltype.typeOf(llvalue), llvalue)
                llops.genop('setfield', [vinst, cname, vvalue])
        else:
            self.rbase.set_vable(llops, vinst, force_cast=True)

    def new_instance(self, llops, classcallhop=None, v_cpytype=None):
        vptr = InstanceRepr.new_instance(self, llops, classcallhop, v_cpytype)
        self.set_vable(llops, vptr)
        return vptr

    def get_namedesc(self, mangled_name):
        TOPPTR = self.get_top_virtualizable_type()
        namedesc = NameDesc(mangled_name, TOPPTR, lltype.Ptr(self.ACCESS))
        return inputconst(lltype.Void, namedesc)
        

    def getfield(self, vinst, attr, llops, force_cast=False):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            cname = self.get_namedesc(mangled_name)
            return llops.gendirectcall(ll_access_get, vinst, cname)
        else:
            return InstanceRepr.getfield(self, vinst, attr, llops, force_cast)

    def setfield(self, vinst, attr, vvalue, llops, force_cast=False, opname='setfield'):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            cname = self.get_namedesc(mangled_name)                
            llops.gendirectcall(ll_access_set, vinst, cname, vvalue)
        else:
            InstanceRepr.setfield(self, vinst, attr, vvalue, llops, force_cast,
                                  opname)
            
class NameDesc(object):
    __metaclass__ = cachedtype
    
    def __init__(self, name, TOPPTR, ACCESSPTR):
        self.name = name
        self.TOPPTR = TOPPTR
        self.ACCESSPTR = ACCESSPTR

    def _freeze_(self):
        return True


def ll_access_get(vinst, namedesc):
    name = namedesc.name
    top = lltype.cast_pointer(namedesc.TOPPTR, vinst)
    access = top.vable_access
    if access:
        return getattr(lltype.cast_pointer(namedesc.ACCESSPTR, access),
                       'get_'+name)(vinst)
    else:
        return getattr(vinst, name)

def ll_access_set(vinst, namedesc, value):
    name = namedesc.name
    top = lltype.cast_pointer(namedesc.TOPPTR, vinst)
    access = top.vable_access    
    if access:
        getattr(lltype.cast_pointer(namedesc.ACCESSPTR, access),
                'set_'+name)(vinst, value)
    else:
        setattr(vinst, name, value)
