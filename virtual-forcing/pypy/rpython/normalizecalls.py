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
from pypy.rpython.rmodel import getgcflavor
from pypy.rlib.objectmodel import instantiate, ComputedIntSymbolic
from pypy.interpreter.argument import Signature

def normalize_call_familes(annotator):
    for callfamily in annotator.bookkeeper.pbc_maximal_call_families.infos():
        if not callfamily.modified:
            assert callfamily.normalized
            continue
        normalize_calltable(annotator, callfamily)
        callfamily.normalized = True
        callfamily.modified = False

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
                progress |= normalize_calltable_row_annotation(annotator,
                                                               row.values())
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
            graph.signature = Signature([argnames[j] for j in argorder], 
                                        None, None)
            # finished
            checkgraph(graph)
            annotator.annotated[newblock] = annotator.annotated[oldblock]
            did_something = True
    return did_something

def normalize_calltable_row_annotation(annotator, graphs):
    if len(graphs) <= 1:
        return False   # nothing to do
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
    all_families = rtyper.annotator.bookkeeper.classpbc_attr_families
    for attrname, access_sets in all_families.items():
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
                    raise TyperError("reading attribute %r: no common base "
                                     "class for %r" % (attrname, descs.keys()))
            extra_access_sets = rtyper.class_pbc_attributes.setdefault(
                commonbase, {})
            if commonbase in rtyper.class_reprs:
                assert access_set in extra_access_sets # minimal sanity check
                continue
            access_set.commonbase = commonbase
            if access_set not in extra_access_sets:
                counter = len(extra_access_sets)
                extra_access_sets[access_set] = attrname, counter

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
        # Note that if classes are in the same callfamily, their __init__
        # attribute must be in the same attrfamily as well.
        change = descs[0].mergeattrfamilies(descs[1:], '__init__')
        if hasattr(descs[0].getuniqueclassdef(), 'my_instantiate_graph'):
            assert not change, "after the fact change to a family of classes" # minimal sanity check
            continue
        # Put __init__ into the attr family, for ClassesPBCRepr.call()
        attrfamily = descs[0].getattrfamily('__init__')
        inits_s = [desc.s_read_attribute('__init__') for desc in descs]
        s_value = annmodel.unionof(attrfamily.s_value, *inits_s)
        attrfamily.s_value = s_value
        # ClassesPBCRepr.call() will also need instantiate() support
        for desc in descs:
            bk.needs_generic_instantiate[desc.getuniqueclassdef()] = True

# ____________________________________________________________

def create_instantiate_functions(annotator):
    # build the 'instantiate() -> instance of C' functions for the vtables

    needs_generic_instantiate = annotator.bookkeeper.needs_generic_instantiate
    
    for classdef in needs_generic_instantiate:
        assert getgcflavor(classdef) == 'gc'   # only gc-case
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

class TotalOrderSymbolic(ComputedIntSymbolic):

    def __init__(self, orderwitness, peers):
        self.orderwitness = orderwitness
        self.peers = peers
        self.value = None
        peers.append(self)

    def __cmp__(self, other):
        if not isinstance(other, TotalOrderSymbolic):
            return cmp(self.compute_fn(), other)
        else:
            return cmp(self.orderwitness, other.orderwitness)

    def compute_fn(self):
        if self.value is None:
            self.peers.sort()
            for i, peer in enumerate(self.peers):
                assert peer.value is None or peer.value == i
                peer.value = i
            assert self.value is not None
        return self.value

    def dump(self, annotator):   # for debugging
        self.peers.sort()
        mapping = {}
        for classdef in annotator.bookkeeper.classdefs:
            if hasattr(classdef, '_unique_cdef_id'):
                mapping[classdef._unique_cdef_id] = classdef
        for peer in self.peers:
            if peer is self:
                print '==>',
            else:
                print '   ',
            print 'value %4s --' % (peer.value,), peer.orderwitness,
            if peer.orderwitness[-1] in mapping:
                print mapping[peer.orderwitness[-1]]
            else:
                print

def assign_inheritance_ids(annotator):
    # we sort the classes by lexicographic order of reversed(mro),
    # which gives a nice depth-first order.  The classes are turned
    # into numbers in order to (1) help determinism, (2) ensure that
    # new hierarchies of classes with no common base classes can be
    # added later and get higher numbers.
    bk = annotator.bookkeeper
    try:
        lst = bk._inheritance_id_symbolics
    except AttributeError:
        lst = bk._inheritance_id_symbolics = []
    for classdef in annotator.bookkeeper.classdefs:
        if not hasattr(classdef, 'minid'):
            witness = [get_unique_cdef_id(cdef) for cdef in classdef.getmro()]
            witness.reverse()
            classdef.minid = TotalOrderSymbolic(witness, lst)
            classdef.maxid = TotalOrderSymbolic(witness + [MAX], lst)

MAX = 1E100
_cdef_id_counter = 0
def get_unique_cdef_id(cdef):
    global _cdef_id_counter
    try:
        return cdef._unique_cdef_id
    except AttributeError:
        cdef._unique_cdef_id = _cdef_id_counter
        _cdef_id_counter += 1
        return cdef._unique_cdef_id

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
