import types
import sys
from pypy.tool.pairtype import pair, pairtype
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Void, Bool, nullptr, frozendict, Ptr, Struct, malloc
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, inputconst, CanBeNull, \
        mangle, inputdesc, warning, impossible_repr
from pypy.rpython import rclass
from pypy.rpython import robject
from pypy.rpython.annlowlevel import llstr

from pypy.rpython import callparse


def small_cand(rtyper, s_pbc):
    if 1 < len(s_pbc.descriptions) < rtyper.getconfig().translation.withsmallfuncsets and \
           hasattr(rtyper.type_system.rpbc, 'SmallFunctionSetPBCRepr'):
        callfamily = s_pbc.descriptions.iterkeys().next().getcallfamily()
        concretetable, uniquerows = get_concrete_calltable(rtyper, callfamily)
        if len(uniquerows) == 1 and (not s_pbc.subset_of or small_cand(rtyper, s_pbc.subset_of)):
            return True
    return False

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
                    getRepr = rtyper.type_system.rpbc.FunctionsPBCRepr
                    if small_cand(rtyper, self):
                        getRepr = rtyper.type_system.rpbc.SmallFunctionSetPBCRepr
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
        if self.subset_of:
            t = self.subset_of.rtyper_makekey()
        else:
            t = ()
        return tuple([self.__class__, self.can_be_None]+lst)+t

##builtin_descriptor_type = (
##    type(len),                            # type 'builtin_function_or_method'
##    type(list.append),                    # type 'method_descriptor'
##    type(type(None).__repr__),            # type 'wrapper_descriptor'
##    type(type.__dict__['__dict__']),      # type 'getset_descriptor'
##    type(type.__dict__['__flags__']),     # type 'member_descriptor'
##    )

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

    if len(uniquerows) == 1:
        uniquerows[0].attrname = None
    else:
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


class AbstractFunctionsPBCRepr(CanBeNull, Repr):
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
                self.lowleveltype = self.setup_specfunc()
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
            result = None
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
                result = self.create_specfunc()
                for attrname, llfn in llfns.items():
                    setattr(result, attrname, llfn)
        self.funccache[funcdesc] = result
        return result

    def convert_const(self, value):
        if isinstance(value, types.MethodType) and value.im_self is None:
            value = value.im_func   # unbound method -> bare function
        if self.lowleveltype is Void:
            return None
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
            return self.get_specfunc_row(llop, v, cname, row.fntype)

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
        if hop.r_result is impossible_repr:
            return None      # see test_always_raising_methods
        else:
            return hop.llops.convertvar(v, rresult, hop.r_result)

class __extend__(pairtype(AbstractFunctionsPBCRepr, AbstractFunctionsPBCRepr)):
        def convert_from_to((r_fpbc1, r_fpbc2), v, llops):
            # this check makes sense because both source and dest repr are FunctionsPBCRepr
            if r_fpbc1.lowleveltype == r_fpbc2.lowleveltype:
                return v
            if r_fpbc1.lowleveltype is Void:
                return inputconst(r_fpbc2, r_fpbc1.s_pbc.const)
            if r_fpbc2.lowleveltype is Void:
                return inputconst(Void, None)
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
            if access1 is not access:
                try:
                    return rtyper.pbc_reprs['unrelated']
                except KeyError:
                    rpbc = rtyper.type_system.rpbc
                    result = rpbc.MultipleUnrelatedFrozenPBCRepr(rtyper)
                    rtyper.pbc_reprs['unrelated'] = result
                    return result
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

    def getstr(self):
        return str(self.frozendesc)
    getstr._annspecialcase_ = 'specialize:memo'

    def ll_str(self, x):
        return self.getstr()


class AbstractMultipleUnrelatedFrozenPBCRepr(CanBeNull, Repr):
    """For a SomePBC of frozen PBCs that have no common access set.
    The only possible operation on such a thing is comparison with 'is'."""

    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.converted_pbc_cache = {}

    def convert_desc(self, frozendesc):
        try:
            return self.converted_pbc_cache[frozendesc]
        except KeyError:
            r = self.rtyper.getrepr(annmodel.SomePBC([frozendesc]))
            if r.lowleveltype is Void:
                # must create a new empty structure, as a placeholder
                pbc = self.create_instance()
            else:
                pbc = r.convert_desc(frozendesc)
            convpbc = self.convert_pbc(pbc)
            self.converted_pbc_cache[frozendesc] = convpbc
            return convpbc

    def convert_const(self, pbc):
        if pbc is None:
            return self.null_instance() 
        if isinstance(pbc, types.MethodType) and pbc.im_self is None:
            value = pbc.im_func   # unbound method -> bare function
        frozendesc = self.rtyper.annotator.bookkeeper.getdesc(pbc)
        return self.convert_desc(frozendesc)

    def rtype_getattr(_, hop):
        if not hop.s_result.is_constant():
            raise TyperError("getattr on a constant PBC returns a non-constant")
        return hop.inputconst(hop.r_result, hop.s_result.const)

class AbstractMultipleFrozenPBCRepr(AbstractMultipleUnrelatedFrozenPBCRepr):
    """For a SomePBC of frozen PBCs with a common attribute access set."""

    def _setup_repr_fields(self):
        fields = []
        self.fieldmap = {}
        if self.access_set is not None:
            attrlist = self.access_set.attrs.keys()
            attrlist.sort()
            for attr in attrlist:
                s_value = self.access_set.attrs[attr]
                r_value = self.rtyper.getrepr(s_value)
                mangled_name = mangle('pbc', attr)
                fields.append((mangled_name, r_value.lowleveltype))
                self.fieldmap[attr] = mangled_name, r_value
        return fields 

    def convert_desc(self, frozendesc):
        if (self.access_set is not None and
            frozendesc not in self.access_set.descs):
            raise TyperError("not found in PBC access set: %r" % (frozendesc,))
        try:
            return self.pbc_cache[frozendesc]
        except KeyError:
            self.setup()
            result = self.create_instance()
            self.pbc_cache[frozendesc] = result
            for attr, (mangled_name, r_value) in self.fieldmap.items():
                if r_value.lowleveltype is Void:
                    continue
                try:
                    thisattrvalue = frozendesc.attrcache[attr]
                except KeyError:
                    if not frozendesc.has_attribute(attr):
                        warning("Desc %r has no attribute %r" % (frozendesc, attr))
                    continue
                llvalue = r_value.convert_const(thisattrvalue)
                setattr(result, mangled_name, llvalue)
            return result

    def rtype_getattr(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)

        attr = hop.args_s[1].const
        vpbc, vattr = hop.inputargs(self, Void)
        v_res = self.getfield(vpbc, attr, hop.llops)
        mangled_name, r_res = self.fieldmap[attr]
        return hop.llops.convertvar(v_res, r_res, hop.r_result)

class __extend__(pairtype(AbstractMultipleFrozenPBCRepr, AbstractMultipleFrozenPBCRepr)):
    def convert_from_to((r_pbc1, r_pbc2), v, llops):
        if r_pbc1.access_set == r_pbc2.access_set:
            return v
        return NotImplemented

class __extend__(pairtype(SingleFrozenPBCRepr, AbstractMultipleFrozenPBCRepr)):
    def convert_from_to((r_pbc1, r_pbc2), v, llops):
        frozendesc1 = r_pbc1.frozendesc
        access = frozendesc1.queryattrfamily()
        if access is r_pbc2.access_set:
            return inputdesc(r_pbc2, frozendesc1)
        return NotImplemented

class __extend__(pairtype(AbstractMultipleUnrelatedFrozenPBCRepr,
                          SingleFrozenPBCRepr)):
    def convert_from_to((r_pbc1, r_pbc2), v, llops):
        return inputconst(Void, r_pbc2.frozendesc)


class MethodOfFrozenPBCRepr(Repr):
    """Representation selected for a PBC of method object(s) of frozen PBCs.
    It assumes that all methods are the same function bound to different PBCs.
    The low-level representation can then be a pointer to that PBC."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.funcdesc = s_pbc.descriptions.keys()[0].funcdesc

        # a hack to force the underlying function to show up in call_families
        # (generally not needed, as normalizecalls() should ensure this,
        # but needed for bound methods that are ll helpers)
        # XXX sort this out
        #call_families = rtyper.annotator.getpbccallfamilies()
        #call_families.find((None, self.function))
        
        if s_pbc.can_be_none():
            raise TyperError("unsupported: variable of type "
                             "method-of-frozen-PBC or None")

        im_selves = []
        for desc in s_pbc.descriptions:
            assert desc.funcdesc is self.funcdesc
            im_selves.append(desc.frozendesc)
            
        self.s_im_self = annmodel.SomePBC(im_selves)
        self.r_im_self = rtyper.getrepr(self.s_im_self)
        self.lowleveltype = self.r_im_self.lowleveltype

    def get_s_callable(self):
        return annmodel.SomePBC([self.funcdesc])

    def get_r_implfunc(self):
        r_func = self.rtyper.getrepr(self.get_s_callable())
        return r_func, 1

    def convert_desc(self, mdesc):
        if mdesc.funcdesc is not self.funcdesc:
            raise TyperError("not a method bound on %r: %r" % (self.funcdesc, 
                                                               mdesc))
        return self.r_im_self.convert_desc(mdesc.frozendesc)

    def convert_const(self, method):
        mdesc = self.rtyper.annotator.bookkeeper.getdesc(method)
        return self.convert_desc(mdesc)

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        # XXX obscure, try to refactor...
        s_function = annmodel.SomePBC([self.funcdesc])
        hop2 = hop.copy()
        hop2.args_s[0] = self.s_im_self   # make the 1st arg stand for 'im_self'
        hop2.args_r[0] = self.r_im_self   # (same lowleveltype as 'self')
        if isinstance(hop2.args_v[0], Constant):
            boundmethod = hop2.args_v[0].value
            hop2.args_v[0] = Constant(boundmethod.im_self)
        if call_args:
            hop2.swap_fst_snd_args()
            _, s_shape = hop2.r_s_popfirstarg() # temporarely remove shape
            adjust_shape(hop2, s_shape)
        # a marker that would crash if actually used...
        c = Constant("obscure-don't-use-me")
        hop2.v_s_insertfirstarg(c, s_function)   # insert 'function'
        # now hop2 looks like simple_call(function, self, args...)
        return hop2.dispatch()

class __extend__(pairtype(MethodOfFrozenPBCRepr, MethodOfFrozenPBCRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        return pair(r_from.r_im_self, r_to.r_im_self).convert_from_to(v, llops)

# __ None ____________________________________________________
class NoneFrozenPBCRepr(Repr):
    lowleveltype = Void

    def rtype_is_true(self, hop):
        return Constant(False, Bool)

    def none_call(self, hop):
        raise TyperError("attempt to call constant None")

    def ll_str(self, none):
        return llstr("None")

    def get_ll_hash_function(self):
        return ll_none_hash

    rtype_simple_call = none_call
    rtype_call_args = none_call

none_frozen_pbc_repr = NoneFrozenPBCRepr()

def ll_none_hash(_):
    return 0


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

# ____________________________________________________________

class AbstractClassesPBCRepr(Repr):
    """Representation selected for a PBC of class(es)."""

    def __init__(self, rtyper, s_pbc):
        self.rtyper = rtyper
        self.s_pbc = s_pbc
        #if s_pbc.can_be_None:
        #    raise TyperError("unsupported: variable of type "
        #                     "class-pointer or None")
        if s_pbc.is_constant():
            self.lowleveltype = Void
        else:
            self.lowleveltype = self.getlowleveltype()

    def get_access_set(self, attrname):
        """Return the ClassAttrFamily corresponding to accesses to 'attrname'
        and the ClassRepr of the class which stores this attribute in
        its vtable.
        """
        classdescs = self.s_pbc.descriptions.keys()
        access = classdescs[0].queryattrfamily(attrname)
        for classdesc in classdescs[1:]:
            access1 = classdesc.queryattrfamily(attrname)
            assert access1 is access       # XXX not implemented
        if access is None:
            raise rclass.MissingRTypeAttribute(attrname)
        commonbase = access.commonbase
        class_repr = rclass.getclassrepr(self.rtyper, commonbase)
        return access, class_repr

    def convert_desc(self, desc):
        if desc not in self.s_pbc.descriptions:
            raise TyperError("%r not in %r" % (cls, self))
        if self.lowleveltype is Void:
            return None
        subclassdef = desc.getuniqueclassdef()
        r_subclass = rclass.getclassrepr(self.rtyper, subclassdef)
        return r_subclass.getruntime(self.lowleveltype)

    def convert_const(self, cls):
        if cls is None:
            if self.lowleveltype is Void:
                return None
            else:
                T = self.lowleveltype
                return self.rtyper.type_system.null_callable(T)
        bk = self.rtyper.annotator.bookkeeper
        classdesc = bk.getdesc(cls)
        return self.convert_desc(classdesc)

    def rtype_getattr(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        else:
            attr = hop.args_s[1].const
            access_set, class_repr = self.get_access_set(attr)
            vcls, vattr = hop.inputargs(class_repr, Void)
            v_res = class_repr.getpbcfield(vcls, access_set, attr, hop.llops)
            s_res = access_set.s_value
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

    def rtype_simple_call(self, hop):
        return self.redispatch_call(hop, call_args=False)

    def rtype_call_args(self, hop):
        return self.redispatch_call(hop, call_args=True)

    def redispatch_call(self, hop, call_args):
        s_instance = hop.s_result
        r_instance = hop.r_result

        if len(self.s_pbc.descriptions) == 1:
            # instantiating a single class
            if self.lowleveltype is not Void:
                assert 0, "XXX None-or-1-class instantation not implemented"
            assert isinstance(s_instance, annmodel.SomeInstance)
            classdef = s_instance.classdef
            s_init = classdef.classdesc.s_read_attribute('__init__')
            v_init = Constant("init-func-dummy")   # this value not really used

            if (isinstance(s_init, annmodel.SomeImpossibleValue) and 
                classdef.classdesc.is_exception_class() and
                classdef.has_no_attrs()):
                # special case for instanciating simple built-in
                # exceptions: always return the same prebuilt instance,
                # and ignore any arguments passed to the contructor.
                r_instance = rclass.getinstancerepr(hop.rtyper, classdef)
                example = r_instance.get_reusable_prebuilt_instance()
                hop.exception_cannot_occur()
                return hop.inputconst(r_instance.lowleveltype, example)

            v_instance = rclass.rtype_new_instance(hop.rtyper, classdef,
                                                   hop.llops, hop)
            if isinstance(v_instance, tuple):
                v_instance, must_call_init = v_instance
                if not must_call_init:
                    return v_instance
        else:
            # instantiating a class from multiple possible classes
            vtypeptr = hop.inputarg(self, arg=0)
            try:
                access_set, r_class = self.get_access_set('__init__')
            except rclass.MissingRTypeAttribute:
                s_init = annmodel.s_ImpossibleValue
            else:
                s_init = access_set.s_value
                v_init = r_class.getpbcfield(vtypeptr, access_set, '__init__',
                                             hop.llops)                
            v_instance = self._instantiate_runtime_class(hop, vtypeptr, r_instance)

        if isinstance(s_init, annmodel.SomeImpossibleValue):
            assert hop.nb_args == 1, ("arguments passed to __init__, "
                                      "but no __init__!")
            hop.exception_cannot_occur()
        else:
            hop2 = self.replace_class_with_inst_arg(
                    hop, v_instance, s_instance, call_args)
            hop2.v_s_insertfirstarg(v_init, s_init)   # add 'initfunc'
            hop2.s_result = annmodel.s_None
            hop2.r_result = self.rtyper.getrepr(hop2.s_result)
            # now hop2 looks like simple_call(initfunc, instance, args...)
            hop2.dispatch()
        return v_instance



class __extend__(pairtype(AbstractClassesPBCRepr, rclass.AbstractClassRepr)):
    def convert_from_to((r_clspbc, r_cls), v, llops):
        # turn a PBC of classes to a standard pointer-to-vtable class repr
        if r_clspbc.lowleveltype == r_cls.lowleveltype:
            return v
        if r_clspbc.lowleveltype is Void:
            return inputconst(r_cls, r_clspbc.s_pbc.const)
        # convert from ptr-to-object-vtable to ptr-to-more-precise-vtable
        return r_cls.fromclasstype(v, llops)

class __extend__(pairtype(AbstractClassesPBCRepr, AbstractClassesPBCRepr)):
    def convert_from_to((r_clspbc1, r_clspbc2), v, llops):
        # this check makes sense because both source and dest repr are ClassesPBCRepr
        if r_clspbc1.lowleveltype == r_clspbc2.lowleveltype:
            return v
        if r_clspbc1.lowleveltype is Void:
            return inputconst(r_clspbc2, r_clspbc1.s_pbc.const)
        if r_clspbc2.lowleveltype is Void:
            return inputconst(Void, r_clspbc2.s_pbc.const)
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
        flags    = mdescs[0].flags
        for mdesc in mdescs[1:]:
            if mdesc.name != methodname:
                raise TyperError("cannot find a unique name under which the "
                                 "methods can be found: %r" % (
                        mdescs,))
            if mdesc.flags != flags:
                raise TyperError("inconsistent 'flags': %r versus %r" % (
                    mdesc.flags, flags))
            classdef = classdef.commonbase(mdesc.selfclassdef)
            if classdef is None:
                raise TyperError("mixing methods coming from instances of "
                                 "classes with no common base: %r" % (mdescs,))

        self.methodname = methodname
        # for ootype, the right thing to do is to always keep the most precise
        # type of the instance, while for lltype we want to cast it to the
        # type where the method is actually defined. See also
        # test_rclass.test_method_specialized_with_subclass and
        # rtyper.attach_methods_to_subclasses
        if self.rtyper.type_system.name == 'ootypesystem':
            self.classdef = classdef
        else:
            self.classdef = classdef.locate_attribute(methodname)
        # the low-level representation is just the bound 'self' argument.
        self.s_im_self = annmodel.SomeInstance(self.classdef, flags=flags)
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

