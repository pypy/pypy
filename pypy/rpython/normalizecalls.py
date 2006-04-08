import py
import types, sys
import inspect
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import checkgraph, FunctionGraph, SpaceOperation
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.tool.sourcetools import has_varargs, valid_identifier
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import needsgc
from pypy.rpython.objectmodel import instantiate, ComputedIntSymbolic

def normalize_call_familes(annotator):
    for callfamily in annotator.bookkeeper.pbc_maximal_call_families.infos():
        normalize_calltable(annotator, callfamily)
        callfamily.normalized = True

def normalize_calltable(annotator, callfamily):
    """Try to normalize all rows of a table."""
    overridden = False
    for desc in callfamily.descs:
        if getattr(desc, 'overridden', False):
            overridden = True
    if overridden:
        if len(callfamily.descs) > 1:
            raise Exception("non-static call to overridden function")
        callfamily.overridden = True
        return
    nshapes = len(callfamily.calltables)
    for shape, table in callfamily.calltables.items():
        for row in table:
            did_something = normalize_calltable_row_signature(annotator, shape,
                                                              row)
            if did_something:
                assert not callfamily.normalized, "change in call family normalisation"
                assert nshapes == 1, "XXX call table too complex"
    while True: 
        progress = False
        for shape, table in callfamily.calltables.items():
            for row in table:
                progress |= normalize_calltable_row_annotation(annotator, row)
        if not progress:
            return   # done
        assert not callfamily.normalized, "change in call family normalisation"

def normalize_calltable_row_signature(annotator, shape, row):
    graphs = row.values()
    assert graphs, "no graph??"
    sig0 = graphs[0].signature
    defaults0 = graphs[0].defaults
    for graph in graphs[1:]:
        if graph.signature != sig0:
            break
        if graph.defaults != defaults0:
            break
    else:
        return False   # nothing to do, all signatures already match
    
    shape_cnt, shape_keys, shape_star, shape_stst = shape
    assert not shape_star, "XXX not implemented"
    assert not shape_stst, "XXX not implemented"

    # for the first 'shape_cnt' arguments we need to generalize to
    # a common type
    call_nbargs = shape_cnt + len(shape_keys)

    did_something = False
    NODEFAULT = object()

    for graph in graphs:
        argnames, varargname, kwargname = graph.signature
        assert not varargname, "XXX not implemented"
        assert not kwargname, "XXX not implemented" # ?
        inputargs_s = [annotator.binding(v) for v in graph.getargs()]
        argorder = range(shape_cnt)
        for key in shape_keys:
            i = list(argnames).index(key)
            assert i not in argorder
            argorder.append(i)
        need_reordering = (argorder != range(call_nbargs))
        if need_reordering or len(graph.getargs()) != call_nbargs:
            oldblock = graph.startblock
            inlist = []
            defaults = graph.defaults or ()
            num_nondefaults = len(inputargs_s) - len(defaults)
            defaults = [NODEFAULT] * num_nondefaults + list(defaults)
            newdefaults = []
            for j in argorder:
                v = Variable(graph.getargs()[j])
                annotator.setbinding(v, inputargs_s[j])
                inlist.append(v)
                newdefaults.append(defaults[j])
            newblock = Block(inlist)
            # prepare the output args of newblock:
            # 1. collect the positional arguments
            outlist = inlist[:shape_cnt]
            # 2. add defaults and keywords
            for j in range(shape_cnt, len(inputargs_s)):
                try:
                    i = argorder.index(j)
                    v = inlist[i]
                except ValueError:
                    default = defaults[j]
                    if default is NODEFAULT:
                        raise TyperError(
                            "call pattern has %d positional arguments, "
                            "but %r takes at least %d arguments" % (
                                shape_cnt, graph.name, num_nondefaults))
                    v = Constant(default)
                outlist.append(v)
            newblock.closeblock(Link(outlist, oldblock))
            oldblock.isstartblock = False
            newblock.isstartblock = True
            graph.startblock = newblock
            for i in range(len(newdefaults)-1,-1,-1):
                if newdefaults[i] is NODEFAULT:
                    newdefaults = newdefaults[i:]
                    break
            graph.defaults = tuple(newdefaults)
            graph.signature = (tuple([argnames[j] for j in argorder]), 
                                   None, None)
            # finished
            checkgraph(graph)
            annotator.annotated[newblock] = annotator.annotated[oldblock]
            did_something = True
    return did_something

def normalize_calltable_row_annotation(annotator, row):
    if len(row) <= 1:
        return False   # nothing to do
    graphs = row.values()
    graph_bindings = {}
    for graph in graphs:
        graph_bindings[graph] = [annotator.binding(v)
                                 for v in graph.getargs()]
    iterbindings = graph_bindings.itervalues()
    nbargs = len(iterbindings.next())
    for binding in iterbindings:
        assert len(binding) == nbargs

    generalizedargs = []
    for i in range(nbargs):
        args_s = []
        for graph, bindings in graph_bindings.items():
            args_s.append(bindings[i])
        s_value = annmodel.unionof(*args_s)
        generalizedargs.append(s_value)
    result_s = [annotator.binding(graph.getreturnvar())
                for graph in graph_bindings]
    generalizedresult = annmodel.unionof(*result_s)

    conversion = False
    for graph in graphs:
        bindings = graph_bindings[graph]
        need_conversion = (generalizedargs != bindings)
        if need_conversion:
            conversion = True
            oldblock = graph.startblock
            inlist = []
            for j, s_value in enumerate(generalizedargs):
                v = Variable(graph.getargs()[j])
                annotator.setbinding(v, s_value)
                inlist.append(v)
            newblock = Block(inlist)
            # prepare the output args of newblock and link
            outlist = inlist[:]
            newblock.closeblock(Link(outlist, oldblock))
            oldblock.isstartblock = False
            newblock.isstartblock = True
            graph.startblock = newblock
            # finished
            checkgraph(graph)
            annotator.annotated[newblock] = annotator.annotated[oldblock]
        # convert the return value too
        if annotator.binding(graph.getreturnvar()) != generalizedresult:
            conversion = True
            annotator.setbinding(graph.getreturnvar(), generalizedresult)

    return conversion

# ____________________________________________________________

def merge_classpbc_getattr_into_classdef(rtyper):
    # code like 'some_class.attr' will record an attribute access in the
    # PBC access set of the family of classes of 'some_class'.  If the classes
    # have corresponding ClassDefs, they are not updated by the annotator.
    # We have to do it now.
    access_sets = rtyper.annotator.bookkeeper.pbc_maximal_access_sets
    for access_set in access_sets.infos():
        descs = access_set.descs
        if len(descs) <= 1:
            continue
        if not isinstance(descs.iterkeys().next(), description.ClassDesc):
            continue
        classdefs = [desc.getuniqueclassdef() for desc in descs]
        commonbase = classdefs[0]
        for cdef in classdefs[1:]:
            commonbase = commonbase.commonbase(cdef)
            if commonbase is None:
                raise TyperError("reading attributes %r: no common base class "
                                 "for %r" % (
                    access_set.attrs.keys(), descs.keys()))
        extra_access_sets = rtyper.class_pbc_attributes.setdefault(commonbase,
                                                                   {})
        if commonbase in rtyper.class_reprs:
            assert access_set in extra_access_sets # minimal sanity check
            return
        access_set.commonbase = commonbase
        if access_set not in extra_access_sets:
            extra_access_sets[access_set] = len(extra_access_sets)

# ____________________________________________________________

def create_class_constructors(annotator):
    bk = annotator.bookkeeper
    call_families = bk.pbc_maximal_call_families

    for family in call_families.infos():
        if len(family.descs) <= 1:
            continue
        descs = family.descs.keys()
        if not isinstance(descs[0], description.ClassDesc):
            continue
        # Note that a callfamily of classes must really be in the same
        # attrfamily as well; This property is relied upon on various
        # places in the rtyper
        change = descs[0].mergeattrfamilies(*descs[1:])
        if hasattr(descs[0].getuniqueclassdef(), 'my_instantiate_graph'):
            assert not change, "after the fact change to a family of classes" # minimal sanity check
            return
        attrfamily = descs[0].getattrfamily()
        # Put __init__ into the attr family, for ClassesPBCRepr.call()
        s_value = attrfamily.attrs.get('__init__', annmodel.s_ImpossibleValue)
        inits_s = [desc.s_read_attribute('__init__') for desc in descs]
        s_value = annmodel.unionof(s_value, *inits_s)
        attrfamily.attrs['__init__'] = s_value
        # ClassesPBCRepr.call() will also need instantiate() support
        for desc in descs:
            bk.needs_generic_instantiate[desc.getuniqueclassdef()] = True

# ____________________________________________________________

def create_instantiate_functions(annotator):
    # build the 'instantiate() -> instance of C' functions for the vtables

    needs_generic_instantiate = annotator.bookkeeper.needs_generic_instantiate
    
    for classdef in needs_generic_instantiate:
        assert needsgc(classdef) # only gc-case
        create_instantiate_function(annotator, classdef)

def create_instantiate_function(annotator, classdef):
    # build the graph of a function that looks like
    # 
    # def my_instantiate():
    #     return instantiate(cls)
    #
    if hasattr(classdef, 'my_instantiate_graph'):
        return
    v = Variable()
    block = Block([])
    block.operations.append(SpaceOperation('instantiate1', [], v))
    name = valid_identifier('instantiate_'+classdef.name)
    graph = FunctionGraph(name, block)
    block.closeblock(Link([v], graph.returnblock))
    annotator.setbinding(v, annmodel.SomeInstance(classdef))
    annotator.annotated[block] = graph
    # force the result to be converted to a generic OBJECTPTR
    generalizedresult = annmodel.SomeInstance(classdef=None)
    annotator.setbinding(graph.getreturnvar(), generalizedresult)
    classdef.my_instantiate_graph = graph
    annotator.translator.graphs.append(graph)

# ____________________________________________________________

class MinIdSymbolic(ComputedIntSymbolic):
    def __init__(self, classdef, rootid):
        self.classdef = classdef
        if classdef is None:
            self.parent = None
        elif classdef.basedef is None:
            self.parent = rootid
        else:
            self.parent = classdef.basedef.minid
        if self.parent:    
            self.parent.children.append(self)
        self.children = []
        if rootid is None:
            self.rootid = self
        else:
            self.rootid = rootid

    def compute_fn(self):
        if self.classdef.minid is self:
            compute_inheritance_ids(self.classdef.bookkeeper)
        return self.classdef.minid

    def __eq__(self, other):
        if isinstance(other, MinIdSymbolic):
            return self is other
        elif isinstance(other, MaxIdSymbolic):
            return False
        raise NotImplementedError

    def __ne__(self, other):
        return not (self == other)

    def __le__(self, other):
        if isinstance(other, MinIdSymbolic):
            common_classdef = self.classdef.commonbase(other.classdef)
            if common_classdef is None:
                baseid = self.rootid
            else:
                baseid = common_classdef.minid
            if baseid is self:
                return True
            if baseid is other:
                return False
            current_self = self
            while current_self.parent is not baseid:
                current_self = current_self.parent
            current_other = other
            while current_other.parent is not baseid:
                current_other = current_other.parent
            selfindex = baseid.children.index(current_self)
            otherindex = baseid.children.index(current_other)
            return selfindex <= otherindex
        elif isinstance(other, MaxIdSymbolic):
            rightmost = other.minid
            while rightmost.children:
                rightmost = rightmost.children[-1]
            return self <= rightmost
        raise NotImplementedError
            
    def compute_inheritance_ids(self, id_=0):
        if self.classdef is not None:
            self.classdef.minid = id_
        maxid = id_
        for child in self.children:
            maxid = child.compute_inheritance_ids(maxid + 1)
        if self.classdef is not None:
            self.classdef.maxid = maxid
        return maxid

class MaxIdSymbolic(ComputedIntSymbolic):
    def __init__(self, minid):
        self.minid = minid

    def compute_fn(self):
        if self.minid.classdef.minid is self.minid:
            compute_inheritance_ids(self.minid.classdef.bookkeeper)
        return self.minid.classdef.maxid

def compute_inheritance_ids(bookkeeper):
    bookkeeper.annotator.rootid.compute_inheritance_ids()
#    def assign_id(classdef, nextid):
#        assert isinstance(classdef.minid, MinIdSymbolic)
#        assert isinstance(classdef.maxid, MaxIdSymbolic)
#        classdef.minid = nextid
#        nextid += 1
#        for subclass in classdef.subdefs:
#            nextid = assign_id(subclass, nextid)
#        classdef.maxid = nextid
#        return classdef.maxid
#    id_ = 0
#    for classdef in bookkeeper.classdefs:
#        if classdef.basedef is None:
#            id_ = assign_id(classdef, id_)
    

def assign_inheritance_ids(annotator):
    if hasattr(annotator, 'rootid'):
        rootid = annotator.rootid
    else:
        rootid = MinIdSymbolic(None, None)
        annotator.rootid = rootid
    def assign_id(classdef):
        if not hasattr(classdef, 'minid'):
            classdef.minid = MinIdSymbolic(classdef, rootid)
        if not hasattr(classdef, 'maxid'):
            classdef.maxid = MaxIdSymbolic(classdef.minid)
        for subclass in classdef.subdefs:
            assign_id(subclass)
    for classdef in annotator.bookkeeper.classdefs:
        
        if classdef.basedef is None:
            assign_id(classdef)

# ____________________________________________________________

def perform_normalizations(rtyper):
    create_class_constructors(rtyper.annotator)
    rtyper.annotator.frozen += 1
    try:
        normalize_call_familes(rtyper.annotator)
        merge_classpbc_getattr_into_classdef(rtyper)
        assign_inheritance_ids(rtyper.annotator)
    finally:
        rtyper.annotator.frozen -= 1
    create_instantiate_functions(rtyper.annotator)
