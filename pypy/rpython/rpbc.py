import types
import sys
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, Bool, nullptr, frozendict, Ptr, Struct, malloc
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, inputconst, HalfConcreteWrapper, CanBeNull
from pypy.rpython import rclass
from pypy.rpython import robject

from pypy.rpython import callparse

class __extend__(annmodel.SomePBC):
    def rtyper_makerepr(self, rtyper):
        if self.isNone():
            return none_frozen_pbc_repr 
        kind = self.getKind()
        if issubclass(kind, description.FunctionDesc):
            sample = self.descriptions.keys()[0]
            callfamily = sample.querycallfamily()
            if callfamily and callfamily.total_calltable_size > 0:
                if sample.overridden:
                    getRepr = OverriddenFunctionPBCRepr
                else:
                    getRepr = FunctionsPBCRepr
            else:
                getRepr = getFrozenPBCRepr
        elif issubclass(kind, description.ClassDesc):
            # user classes
            getRepr = rtyper.type_system.rpbc.ClassesPBCRepr
            # XXX what about this?
##                 elif type(x) is type and x.__module__ in sys.builtin_module_names:
##                     # special case for built-in types, seen in faking
##                     getRepr = getPyObjRepr
        elif issubclass(kind, description.MethodDesc):
            getRepr = rtyper.type_system.rpbc.MethodsPBCRepr
        elif issubclass(kind, description.FrozenDesc):
            getRepr = getFrozenPBCRepr
        elif issubclass(kind, description.MethodOfFrozenDesc):
            getRepr = rtyper.type_system.rpbc.MethodOfFrozenPBCRepr
        else:
            raise TyperError("unexpected PBC kind %r"%(kind,))

##             elif isinstance(x, builtin_descriptor_type):
##                 # strange built-in functions, method objects, etc. from fake.py
##                 getRepr = getPyObjRepr


        return getRepr(rtyper, self)

    def rtyper_makekey(self):
        lst = list(self.descriptions)
        lst.sort()
        return tuple([self.__class__, self.can_be_None]+lst)

builtin_descriptor_type = (
    type(len),                             # type 'builtin_function_or_method'
    type(list.append),                     # type 'method_descriptor'
    type(type(None).__repr__),             # type 'wrapper_descriptor'
    type(type.__dict__['__dict__']),       # type 'getset_descriptor'
    type(type.__dict__['__basicsize__']),  # type 'member_descriptor'
    )

# ____________________________________________________________

class ConcreteCallTableRow(dict):
    """A row in a concrete call table."""

def build_concrete_calltable(rtyper, callfamily):
    """Build a complete call table of a call family
    with concrete low-level function objs.
    """
    concretetable = {}   # (shape,index): row, maybe with duplicates
    uniquerows = []      # list of rows, without duplicates
    
    def lookuprow(row):
        # a 'matching' row is one that has the same llfn, expect
        # that it may have more or less 'holes'
        for existingindex, existingrow in enumerate(uniquerows):
            if row.fntype != existingrow.fntype:
                continue   # not the same pointer type, cannot match
            for funcdesc, llfn in row.items():
                if funcdesc in existingrow:
                    if llfn != existingrow[funcdesc]:
                        break   # mismatch
            else:
                # potential match, unless the two rows have no common funcdesc
                merged = ConcreteCallTableRow(row)
                merged.update(existingrow)
                merged.fntype = row.fntype
                if len(merged) == len(row) + len(existingrow):
                    pass   # no common funcdesc, not a match
                else:
                    return existingindex, merged
        raise LookupError

    def addrow(row):
        # add a row to the table, potentially merging it with an existing row
        try:
            index, merged = lookuprow(row)
        except LookupError:
            uniquerows.append(row)   # new row
        else:
            if merged == uniquerows[index]:
                pass    # already exactly in the table
            else:
                del uniquerows[index]
                addrow(merged)   # add the potentially larger merged row

    concreterows = {}
    for shape, rows in callfamily.calltables.items():
        for index, row in enumerate(rows):
            concreterow = ConcreteCallTableRow()
            for funcdesc, graph in row.items():
                llfn = rtyper.getcallable(graph)
                concreterow[funcdesc] = llfn
            assert len(concreterow) > 0
            concreterow.fntype = typeOf(llfn)   # 'llfn' from the loop above
                                         # (they should all have the same type)
            concreterows[shape, index] = concreterow

    for row in concreterows.values():
        addrow(row)

    for (shape, index), row in concreterows.items():
        existingindex, biggerrow = lookuprow(row)
        row = uniquerows[existingindex]
        assert biggerrow == row   # otherwise, addrow() is broken
        concretetable[shape, index] = row

    for finalindex, row in enumerate(uniquerows):
        row.attrname = 'variant%d' % finalindex

    return concretetable, uniquerows

def get_concrete_calltable(rtyper, callfamily):
    """Get a complete call table of a call family
    with concrete low-level function objs.
    """
    # cache on the callfamily
    try:
        cached = rtyper.concrete_calltables[callfamily]
    except KeyError:
        concretetable, uniquerows = build_concrete_calltable(rtyper, callfamily)
        cached = concretetable, uniquerows, callfamily.total_calltable_size
        rtyper.concrete_calltables[callfamily] = cached
    else:
        concretetable, uniquerows, oldsize = cached
        if oldsize != callfamily.total_calltable_size:
            raise TyperError("call table was unexpectedly extended")
    return concretetable, uniquerows


class FunctionsPBCRepr(CanBeNull, Repr):
    """Representation selected for a PBC of function(s)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        self.callfamily = s_pbc.descriptions.iterkeys().next().getcallfamily()
        if len(s_pbc.descriptions) == 1 and not s_pbc.can_be_None:
            # a single function
            self.lowleveltype = Void
        else:
            concretetable, uniquerows = get_concrete_calltable(self.rtyper,
                                                               self.callfamily)
            self.concretetable = concretetable
            self.uniquerows = uniquerows
            if len(uniquerows) == 1:
                row = uniquerows[0]
                self.lowleveltype = row.fntype
            else:
                # several functions, each with several specialized variants.
                # each function becomes a pointer to a Struct containing
                # pointers to its variants.
                fields = []
                for row in uniquerows:
                    fields.append((row.attrname, row.fntype))
                self.lowleveltype = Ptr(Struct('specfunc', *fields))
        self.funccache = {}

    def get_s_callable(self):
        return self.s_pbc

    def get_r_implfunc(self):
        return self, 0

    def get_s_signatures(self, shape):
        funcdesc = self.s_pbc.descriptions.iterkeys().next()
        return funcdesc.get_s_signatures(shape)

##    def function_signatures(self):
##        if self._function_signatures is None:
##            self._function_signatures = {}
##            for func in self.s_pbc.prebuiltinstances:
##                if func is not None:
##                    self._function_signatures[func] = getsignature(self.rtyper,
##                                                                   func)
##            assert self._function_signatures
##        return self._function_signatures

    def convert_desc(self, funcdesc):
        # get the whole "column" of the call table corresponding to this desc
        try:
            return self.funccache[funcdesc]
        except KeyError:
            pass
        if self.lowleveltype is Void:
            result = HalfConcreteWrapper(self.get_unique_llfn)
        else:
            llfns = {}
            found_anything = False
            for row in self.uniquerows:
                if funcdesc in row:
                    llfn = row[funcdesc]
                    found_anything = True
                else:
                    # missing entry -- need a 'null' of the type that matches
                    # this row
                    llfn = self.rtyper.type_system.null_callable(row.fntype)
                llfns[row.attrname] = llfn
            if not found_anything:
                raise TyperError("%r not in %r" % (funcdesc,
                                                   self.s_pbc.descriptions))
            if len(self.uniquerows) == 1:
                result = llfn   # from the loop above
            else:
                # build a Struct with all the values collected in 'llfns'
                result = malloc(self.lowleveltype.TO, immortal=True)
                for attrname, llfn in llfns.items():
                    setattr(result, attrname, llfn)
        self.funccache[funcdesc] = result
        return result

    def convert_const(self, value):
        if isinstance(value, types.MethodType) and value.im_self is None:
            value = value.im_func   # unbound method -> bare function
        if self.lowleveltype is Void:
            return HalfConcreteWrapper(self.get_unique_llfn)
        if value is None:
            null = self.rtyper.type_system.null_callable(self.lowleveltype)
            return null
        funcdesc = self.rtyper.annotator.bookkeeper.getdesc(value)
        return self.convert_desc(funcdesc)

    def convert_to_concrete_llfn(self, v, shape, index, llop):
        """Convert the variable 'v' to a variable referring to a concrete
        low-level function.  In case the call table contains multiple rows,
        'index' and 'shape' tells which of its items we are interested in.
        """
        assert v.concretetype == self.lowleveltype
        if self.lowleveltype is Void:
            assert len(self.s_pbc.descriptions) == 1
                                      # lowleveltype wouldn't be Void otherwise
            funcdesc, = self.s_pbc.descriptions
            row_of_one_graph = self.callfamily.calltables[shape][index]
            graph = row_of_one_graph[funcdesc]
            llfn = self.rtyper.getcallable(graph)
            return inputconst(typeOf(llfn), llfn)
        elif len(self.uniquerows) == 1:
            return v
        else:
            # 'v' is a Struct pointer, read the corresponding field
            row = self.concretetable[shape, index]
            cname = inputconst(Void, row.attrname)
            return llop.genop('getfield', [v, cname], resulttype = row.fntype)

    def get_unique_llfn(self):
        # try to build a unique low-level function.  Avoid to use
        # whenever possible!  Doesn't work with specialization, multiple
        # different call sites, etc.
        if self.lowleveltype is not Void:
            raise TyperError("cannot pass multiple functions here")
        assert len(self.s_pbc.descriptions) == 1
                                  # lowleveltype wouldn't be Void otherwise
        funcdesc, = self.s_pbc.descriptions
        if len(self.callfamily.calltables) != 1:
            raise TyperError("cannot pass a function with various call shapes")
        table, = self.callfamily.calltables.values()
        graphs = []
        for row in table:
            if funcdesc in row:
                graphs.append(row[funcdesc])
        if not graphs:
            raise TyperError("cannot pass here a function that is not called")
        graph = graphs[0]
        if graphs != [graph]*len(graphs):
            raise TyperError("cannot pass a specialized function here")
        llfn = self.rtyper.getcallable(graph)
        return inputconst(typeOf(llfn), llfn)

    def rtype_simple_call(self, hop):
        return self.call('simple_call', hop)

    def rtype_call_args(self, hop):
        return self.call('call_args', hop)

    def call(self, opname, hop):
        bk = self.rtyper.annotator.bookkeeper
        args = bk.build_args(opname, hop.args_s[1:])
        s_pbc = hop.args_s[0]   # possibly more precise than self.s_pbc
        descs = s_pbc.descriptions.keys()
        shape, index = description.FunctionDesc.variant_for_call_site(bk, self.callfamily, descs, args)
        row_of_graphs = self.callfamily.calltables[shape][index]
        anygraph = row_of_graphs.itervalues().next()  # pick any witness
        vfn = hop.inputarg(self, arg=0)
        vlist = [self.convert_to_concrete_llfn(vfn, shape, index,
                                               hop.llops)]
        vlist += callparse.callparse(self.rtyper, anygraph, hop, opname)
        rresult = callparse.getrresult(self.rtyper, anygraph)
        hop.exception_is_here()
        if isinstance(vlist[0], Constant):
            v = hop.genop('direct_call', vlist, resulttype = rresult)
        else:
            vlist.append(hop.inputconst(Void, row_of_graphs.values()))
            v = hop.genop('indirect_call', vlist, resulttype = rresult)
        return hop.llops.convertvar(v, rresult, hop.r_result)

class __extend__(pairtype(FunctionsPBCRepr, FunctionsPBCRepr)):
        def convert_from_to((r_fpbc1, r_fpbc2), v, llops):
            # this check makes sense because both source and dest repr are FunctionsPBCRepr
            if r_fpbc1.lowleveltype == r_fpbc2.lowleveltype:
                return v
            if r_fpbc1.lowleveltype is Void:
                return inputconst(r_fpbc2, r_fpbc1.s_pbc.const)
            return NotImplemented

class OverriddenFunctionPBCRepr(Repr):
    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        assert len(s_pbc.descriptions) == 1
        self.lowleveltype = Void

    def rtype_simple_call(self, hop):
        from pypy.rpython.rspecialcase import rtype_call_specialcase
        return rtype_call_specialcase(hop)
        
def getPyObjRepr(rtyper, s_pbc):
    return robject.pyobj_repr

def getFrozenPBCRepr(rtyper, s_pbc):
    descs = s_pbc.descriptions.keys()
    assert len(descs) >= 1
    if len(descs) == 1 and not s_pbc.can_be_None:
        return SingleFrozenPBCRepr(descs[0])
    else:
        access = descs[0].queryattrfamily()
        for desc in descs[1:]:
            access1 = desc.queryattrfamily()
            assert access1 is access       # XXX not implemented
        try:
            return rtyper.pbc_reprs[access]
        except KeyError:
            result = rtyper.type_system.rpbc.MultipleFrozenPBCRepr(rtyper,
                                                                   access)
            rtyper.pbc_reprs[access] = result
            rtyper.add_pendingsetup(result) 
            return result


class SingleFrozenPBCRepr(Repr):
    """Representation selected for a single non-callable pre-built constant."""
    lowleveltype = Void

    def __init__(self, frozendesc):
        self.frozendesc = frozendesc

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)

    def convert_desc(self, frozendesc):
        assert frozendesc is self.frozendesc
        return object()  # lowleveltype is Void

# __ None ____________________________________________________
class NoneFrozenPBCRepr(SingleFrozenPBCRepr):
    
    def rtype_is_true(self, hop):
        return Constant(False, Bool)

none_frozen_pbc_repr = NoneFrozenPBCRepr(None)


class __extend__(pairtype(Repr, NoneFrozenPBCRepr)):

    def convert_from_to((r_from, _), v, llops):
        return inputconst(Void, None)
    
    def rtype_is_((robj1, rnone2), hop):
        return hop.rtyper.type_system.rpbc.rtype_is_None(robj1, rnone2, hop)

class __extend__(pairtype(NoneFrozenPBCRepr, Repr)):

    def convert_from_to((_, r_to), v, llops):
        return inputconst(r_to, None)

    def rtype_is_((rnone1, robj2), hop):
        return hop.rtyper.type_system.rpbc.rtype_is_None(
                                                robj2, rnone1, hop, pos=1)
        
class __extend__(pairtype(NoneFrozenPBCRepr, robject.PyObjRepr)):

    def convert_from_to(_, v, llops):
        return inputconst(robject.pyobj_repr, None)

# ____________________________________________________________

class AbstractClassesPBCRepr(Repr):
    """Representation selected for a PBC of class(es)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        if s_pbc.can_be_None:
            raise TyperError("unsupported: variable of type "
                             "class-pointer or None")
        if s_pbc.is_constant():
            self.lowleveltype = Void
        else:
            self.lowleveltype = rtyper.type_system.rclass.CLASSTYPE
        self._access_set = None
        self._class_repr = None

    def get_access_set(self):
        if self._access_set is None:
            classdescs = self.s_pbc.descriptions.keys()
            access = classdescs[0].getattrfamily()
            for classdesc in classdescs[1:]:
                access1 = classdesc.getattrfamily() 
                assert access1 is access       # XXX not implemented
            commonbase = access.commonbase
            self._class_repr = rclass.getclassrepr(self.rtyper, commonbase)
            self._access_set = access
        return self._access_set

    def get_class_repr(self):
        self.get_access_set()
        return self._class_repr

    def convert_desc(self, desc):
        if desc not in self.s_pbc.descriptions:
            raise TyperError("%r not in %r" % (cls, self))
        if self.lowleveltype is Void:
            return desc.pyobj
        return rclass.get_type_repr(self.rtyper).convert_desc(desc)

    def convert_const(self, cls):
        bk = self.rtyper.annotator.bookkeeper
        classdesc = bk.getdesc(cls)
        return self.convert_desc(classdesc)

    def rtype_getattr(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        else:
            attr = hop.args_s[1].const
            access_set = self.get_access_set()
            class_repr = self.get_class_repr()
            vcls, vattr = hop.inputargs(class_repr, Void)
            v_res = class_repr.getpbcfield(vcls, access_set, attr, hop.llops)
            s_res = access_set.attrs[attr]
            r_res = self.rtyper.getrepr(s_res)
            return hop.llops.convertvar(v_res, r_res, hop.r_result)

    def replace_class_with_inst_arg(self, hop, v_inst, s_inst, call_args):
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()   # discard the class pointer argument
        if call_args:
            _, s_shape = hop2.r_s_popfirstarg() # temporarely remove shape
            hop2.v_s_insertfirstarg(v_inst, s_inst)  # add 'instance'
            adjust_shape(hop2, s_shape)
        else:
            hop2.v_s_insertfirstarg(v_inst, s_inst)  # add 'instance'
        return hop2


class __extend__(pairtype(AbstractClassesPBCRepr, rclass.AbstractClassRepr)):
    def convert_from_to((r_clspbc, r_cls), v, llops):
        # turn a PBC of classes to a standard pointer-to-vtable class repr
        if r_clspbc.lowleveltype == r_cls.lowleveltype:
            return v
        if r_clspbc.lowleveltype is Void:
            return inputconst(r_cls, r_clspbc.s_pbc.const)
        # convert from ptr-to-object-vtable to ptr-to-more-precise-vtable
        # but first check if it is safe
        assert (r_clspbc.lowleveltype ==
            r_clspbc.rtyper.type_system.rclass.CLASSTYPE)
        if not r_clspbc.get_class_repr().classdef.issubclass(r_cls.classdef):
            return NotImplemented
        return r_cls.fromtypeptr(v, llops)

class __extend__(pairtype(AbstractClassesPBCRepr, AbstractClassesPBCRepr)):
    def convert_from_to((r_clspbc1, r_clspbc2), v, llops):
        # this check makes sense because both source and dest repr are ClassesPBCRepr
        if r_clspbc1.lowleveltype == r_clspbc2.lowleveltype:
            return v
        if r_clspbc1.lowleveltype is Void:
            return inputconst(r_clspbc2, r_clspbc1.s_pbc.const)
        return NotImplemented

def adjust_shape(hop2, s_shape):
    new_shape = (s_shape.const[0]+1,) + s_shape.const[1:]
    c_shape = Constant(new_shape)
    s_shape = hop2.rtyper.annotator.bookkeeper.immutablevalue(new_shape)
    hop2.v_s_insertfirstarg(c_shape, s_shape) # reinsert adjusted shape

class AbstractMethodsPBCRepr(Repr):
    """Representation selected for a PBC of MethodDescs.
    It assumes that all the methods come from the same name and have
    been read from instances with a common base."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        if s_pbc.isNone():
            raise TyperError("unsupported: variable of type "
                             "bound-method-object or None")
        mdescs = s_pbc.descriptions.keys()
        methodname = mdescs[0].name
        classdef = mdescs[0].selfclassdef
        for mdesc in mdescs[1:]:
            if mdesc.name != methodname:
                raise TyperError("cannot find a unique name under which the "
                                 "methods can be found: %r" % (
                        mdescs,))
            classdef = classdef.commonbase(mdesc.selfclassdef)
            if classdef is None:
                raise TyperError("mixing methods coming from instances of "
                                 "classes with no common base: %r" % (mdescs,))

        self.methodname = methodname
        self.classdef = classdef.locate_attribute(methodname)
        # the low-level representation is just the bound 'self' argument.
        self.s_im_self = annmodel.SomeInstance(self.classdef)
        self.r_im_self = rclass.getinstancerepr(rtyper, self.classdef)
        self.lowleveltype = self.r_im_self.lowleveltype

    def convert_const(self, method):
        if getattr(method, 'im_func', None) is None:
            raise TyperError("not a bound method: %r" % method)
        return self.r_im_self.convert_const(method.im_self)

    def get_r_implfunc(self):
        r_class = self.r_im_self.rclass
        mangled_name, r_func = r_class.clsfields[self.methodname]
        return r_func, 1

    def get_s_callable(self):
        return self.s_pbc

    def get_method_from_instance(self, r_inst, v_inst, llops):
        # The 'self' might have to be cast to a parent class
        # (as shown for example in test_rclass/test_method_both_A_and_B)
        return llops.convertvar(v_inst, r_inst, self.r_im_self)

    def add_instance_arg_to_hop(self, hop, call_args):
        hop2 = hop.copy()
        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')

        if call_args:
            hop2.swap_fst_snd_args()
            _, s_shape = hop2.r_s_popfirstarg()
            adjust_shape(hop2, s_shape)
        return hop2
# ____________________________________________________________

##def getsignature(rtyper, func):
##    f = rtyper.getcallable(func)
##    graph = rtyper.type_system_deref(f).graph
##    rinputs = [rtyper.bindingrepr(v) for v in graph.getargs()]
##    if graph.getreturnvar() in rtyper.annotator.bindings:
##        rresult = rtyper.bindingrepr(graph.getreturnvar())
##    else:
##        rresult = Void
##    return f, rinputs, rresult

def samesig(funcs):
    import inspect
    argspec = inspect.getargspec(funcs[0])
    for func in funcs:
        if inspect.getargspec(func) != argspec:
            return False
    return True

# ____________________________________________________________

def commonbase(classdefs):
    result = classdefs[0]
    for cdef in classdefs[1:]:
        result = result.commonbase(cdef)
        if result is None:
            raise TyperError("no common base class in %r" % (classdefs,))
    return result

def allattributenames(classdef):
    for cdef1 in classdef.getmro():
        for attrname in cdef1.attrs:
            yield cdef1, attrname

