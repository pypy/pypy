from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem.rclass import InstanceRepr
from pypy.rpython.annlowlevel import cachedtype

class VirtualizableInstanceRepr(InstanceRepr):

    def __init__(self, rtyper, classdef):
        InstanceRepr.__init__(self, rtyper, classdef)
        classdesc = classdef.classdesc
        assert '_virtualizable_' in classdesc.classdict
        basedesc = classdesc.basedesc
        assert basedesc is None or basedesc.lookup('_virtualizable_') is None
        # xxx check that the parents have no instance field

    def _setup_repr(self):
        llfields = []
        ACCESS = lltype.ForwardReference()
        llfields.append(('vable_access', lltype.Ptr(ACCESS)))
        InstanceRepr._setup_repr(self, llfields)
        name = self.lowleveltype.TO._name
        accessors = []
        SELF = self.lowleveltype
        for name, (mangled_name, r) in self.fields.items():
            T = r.lowleveltype
            GETTER = lltype.Ptr(lltype.FuncType([SELF], T))
            SETTER = lltype.Ptr(lltype.FuncType([SELF, T], lltype.Void))
            accessors.append(('get_'+mangled_name, GETTER))
            accessors.append(('set_'+mangled_name, SETTER))
        ACCESS.become(lltype.Struct(name+'_access', *accessors))
        self.ACCESS = ACCESS

    def set_vable(self, llops, vinst, name, llvalue):
        cname = inputconst(lltype.Void, 'vable_'+name)
        vvalue = inputconst(lltype.typeOf(llvalue), llvalue)
        llops.genop('setfield', [vinst, cname, vvalue])

    def new_instance(self, llops, classcallhop=None, v_cpytype=None):
        vptr = InstanceRepr.new_instance(self, llops, classcallhop, v_cpytype)
        self.set_vable(llops, vptr, 'access', lltype.nullptr(self.ACCESS))
        return vptr

    def getfield(self, vinst, attr, llops, force_cast=False):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            cname = inputconst(lltype.Void, NameDesc(mangled_name))
            return llops.gendirectcall(ll_access_get, vinst, cname)
        else:
            return InstanceRepr.getfield(vinst, attr, llops, force_cast)

class NameDesc(object):
    __metaclass__ = cachedtype
    
    def __init__(self, name):
        self.name = name

    def _freeze_(self):
        return True


def ll_access_get(vinst, namedesc):
    access = vinst.vable_access
    name = namedesc.name
    if access:
        return getattr(access, 'get_'+name)(vinst)
    else:
        return getattr(vinst, name)
