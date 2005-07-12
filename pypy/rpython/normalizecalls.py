import py
import types
import inspect
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, checkgraph
from pypy.annotation import model as annmodel
from pypy.tool.sourcetools import has_varargs
from pypy.rpython.rmodel import TyperError


def normalize_function_signatures(annotator):
    """Make sure that all functions called in a group have exactly
    the same signature, by hacking their flow graphs if needed.
    """
    call_families = annotator.getpbccallfamilies()

    # for methods, we create or complete a corresponding function-only
    # family with call patterns that have the extra 'self' argument
    for family in call_families.infos():
        prevkey = None
        for classdef, func in family.objects:
            if classdef is not None:
                # add (None, func) to the func_family
                if prevkey is None:
                    prevkey = (None, func)
                else:
                    call_families.union((None, func), prevkey)
        if prevkey is not None:
            # copy the patterns from family to func_family with the
            # extra self argument
            _, _, func_family = call_families.find(prevkey)
            for pattern in family.patterns:
                argcount = pattern[0]
                pattern = (argcount+1,) + pattern[1:]
                func_family.patterns[pattern] = True

    # for bound method objects, make sure the im_func shows up too.
    for family in call_families.infos():
        first = family.objects.keys()[0][1]
        for _, callable in family.objects:
            if isinstance(callable, types.MethodType):
                # for bound methods families for now just accept and check that
                # they all refer to the same function
                if not isinstance(first, types.MethodType):
                    raise TyperError("call family with both bound methods and "
                                     "%r" % (first,))
                if first.im_func is not callable.im_func:
                    raise TyperError("call family of bound methods: should all "
                                     "refer to the same function")
        # create a family for the common im_func
        if isinstance(first, types.MethodType):
            _, _, func_family = call_families.find((None, first.im_func))
            for pattern in family.patterns:
                argcount = pattern[0]
                pattern = (argcount+1,) + pattern[1:]
                func_family.patterns[pattern] = True

    # find the most general signature of each family
    for family in call_families.infos():
        # collect functions in this family, ignoring:
        #  - methods: taken care of above
        #  - bound methods: their im_func will also show up
        #  - classes: already handled by create_class_constructors()
        functions = [func for classdef, func in family.objects
                          if classdef is None and
                not isinstance(func, (type, types.ClassType, types.MethodType))]
        if len(functions) > 1:  # otherwise, nothing to do
            if len(family.patterns) > 1:
                raise TyperError("don't support multiple call patterns "
                                 "to multiple functions for now %r" % (
                    functions))
            pattern, = family.patterns
            shape_cnt, shape_keys, shape_star, shape_stst = pattern
            assert not shape_star, "XXX not implemented"
            assert not shape_stst, "XXX not implemented"

            # for the first 'shape_cnt' arguments we need to generalize to
            # a common type
            graph_bindings = {}
            graph_argorders = {}
            for func in functions:
                assert not has_varargs(func), "XXX not implemented"
                try:
                    graph = annotator.translator.flowgraphs[func]
                except KeyError:
                    raise TyperError("the skipped %r must not show up in a "
                                     "call family" % (func,))
                graph_bindings[graph] = [annotator.binding(v)
                                         for v in graph.getargs()]
                argorder = range(shape_cnt)
                for key in shape_keys:
                    i = list(func.func_code.co_varnames).index(key)
                    assert i not in argorder
                    argorder.append(i)
                graph_argorders[graph] = argorder

            call_nbargs = shape_cnt + len(shape_keys)
            generalizedargs = []
            for i in range(call_nbargs):
                args_s = []
                for graph, bindings in graph_bindings.items():
                    j = graph_argorders[graph][i]
                    args_s.append(bindings[j])
                s_value = annmodel.unionof(*args_s)
                generalizedargs.append(s_value)
            result_s = [annotator.binding(graph.getreturnvar())
                        for graph in graph_bindings]
            generalizedresult = annmodel.unionof(*result_s)

            for func in functions:
                graph = annotator.translator.getflowgraph(func)
                bindings = graph_bindings[graph]
                argorder = graph_argorders[graph]
                need_reordering = (argorder != range(call_nbargs))
                need_conversion = (generalizedargs != bindings)
                if need_reordering or need_conversion:
                    oldblock = graph.startblock
                    inlist = []
                    for s_value, j in zip(generalizedargs, argorder):
                        v = Variable(graph.getargs()[j])
                        annotator.setbinding(v, s_value)
                        inlist.append(v)
                    newblock = Block(inlist)
                    # prepare the output args of newblock:
                    # 1. collect the positional arguments
                    outlist = inlist[:shape_cnt]
                    # 2. add defaults and keywords
                    defaults = func.func_defaults or ()
                    for j in range(shape_cnt, len(bindings)):
                        try:
                            i = argorder.index(j)
                            v = inlist[i]
                        except ValueError:
                            try:
                                default = defaults[j-len(bindings)]
                            except IndexError:
                                raise TyperError(
                                    "call pattern has %d positional arguments, "
                                    "but %r takes at least %d arguments" % (
                                        shape_cnt, func,
                                        len(bindings) - len(defaults)))
                            v = Constant(default)
                        outlist.append(v)
                    newblock.closeblock(Link(outlist, oldblock))
                    oldblock.isstartblock = False
                    newblock.isstartblock = True
                    graph.startblock = newblock
                    # finished
                    checkgraph(graph)
                    annotator.annotated[newblock] = annotator.annotated[oldblock]
                graph.normalized_for_calls = True
                # convert the return value too
                annotator.setbinding(graph.getreturnvar(), generalizedresult)


def specialize_pbcs_by_memotables(annotator):
    memo_tables = annotator.bookkeeper.memo_tables
    access_sets = annotator.getpbcaccesssets()
    for memo_table in memo_tables: 
        arglist_s = memo_table.arglist_s 
        assert len(arglist_s) == 1, "XXX implement >1 arguments" 
        arg1 = arglist_s[0]
        assert isinstance(arg1, annmodel.SomePBC)

        if None in arg1.prebuiltinstances:
            raise TyperError("unsupported: memo call with an argument that can be None")
        pbcs = arg1.prebuiltinstances.keys()
        _, _, access_set = access_sets.find(pbcs[0])

        # enforce a structure where we can uniformly access 
        # our memofield later 
        for pbc in pbcs[1:]:
            _, _, access_set = access_sets.union(pbcs[0], pbc)
        
        # we can have multiple memo_tables per PBC 
        i = 0
        while 1: 
            fieldname = "memofield_%d" % i
            if fieldname in access_set.attrs: 
                i += 1
                continue
            memo_table.fieldname = fieldname
            break
        access_set.attrs[fieldname] = memo_table.s_result
        for pbc in pbcs: 
            value = memo_table.table[(pbc,)] 
            access_set.values[(pbc, fieldname)] = value 

def merge_classpbc_getattr_into_classdef(rtyper):
    # code like 'some_class.attr' will record an attribute access in the
    # PBC access set of the family of classes of 'some_class'.  If the classes
    # have corresponding ClassDefs, they are not updated by the annotator.
    # We have to do it now.
    access_sets = rtyper.annotator.getpbcaccesssets()
    userclasses = rtyper.annotator.getuserclasses()
    for access_set in access_sets.infos():
        if len(access_set.objects) <= 1:
            continue
        count = 0
        for obj in access_set.objects:
            if obj in userclasses:
                count += 1
        if count == 0:
            continue
        if count != len(access_set.objects):
            raise TyperError("reading attributes %r: mixing instantiated "
                             "classes with something else in %r" % (
                access_set.attrs.keys(), access_set.objects.keys()))
        classdefs = [userclasses[obj] for obj in access_set.objects]
        commonbase = classdefs[0]
        for cdef in classdefs[1:]:
            commonbase = commonbase.commonbase(cdef)
            if commonbase is None:
                raise TyperError("reading attributes %r: no common base class "
                                 "for %r" % (
                    access_set.attrs.keys(), access_set.objects.keys()))
        access_set.commonbase = commonbase
        extra_access_sets = rtyper.class_pbc_attributes.setdefault(commonbase,
                                                                   {})
        extra_access_sets[access_set] = len(extra_access_sets)

def create_class_constructors(rtyper):
    # for classes that appear in families, make a __new__ PBC attribute.
    call_families = rtyper.annotator.getpbccallfamilies()
    access_sets = rtyper.annotator.getpbcaccesssets()

    for family in call_families.infos():
        if len(family.objects) <= 1:
            continue
        count = 0
        for _, klass in family.objects:
            if isinstance(klass, (type, types.ClassType)):
                count += 1
        if count == 0:
            continue
        if count != len(family.objects):
            raise TyperError("calls to mixed class/non-class objects in the "
                             "family %r" % family.objects.keys())

        klasses = [klass for (_, klass) in family.objects.keys()]
        functions = {}
        function_values = {}
        for klass in klasses:
            try:
                initfunc = klass.__init__.im_func
            except AttributeError:
                initfunc = None
            # XXX AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARGH
            #     bouh.
            if initfunc:
                args, varargs, varkw, defaults = inspect.getargspec(initfunc)
            else:
                args, varargs, varkw, defaults = ('self',), None, None, ()
            args = list(args)
            args2 = args[:]
            if defaults:
                for i in range(-len(defaults), 0):
                    args[i] += '=None'
            if varargs:
                args.append('*%s' % varargs)
                args2.append('*%s' % varargs)
            if varkw:
                args.append('**%s' % varkw)
                args2.append('**%s' % varkw)
            args.pop(0)   # 'self'
            args2.pop(0)   # 'self'
            funcsig = ', '.join(args)
            callsig = ', '.join(args2)
            source = py.code.Source('''
                def %s__new__(%s):
                    return ____class(%s)
            ''' % (
                klass.__name__, funcsig, callsig))
            miniglobals = {
                '____class': klass,
                }
            exec source.compile() in miniglobals
            klass__new__ = miniglobals['%s__new__' % klass.__name__]
            if initfunc:
                klass__new__.func_defaults = initfunc.func_defaults
                graph = rtyper.annotator.translator.getflowgraph(initfunc)
                args_s = [rtyper.annotator.binding(v) for v in graph.getargs()]
                args_s.pop(0)   # 'self'
            else:
                args_s = []
            rtyper.annotator.build_types(klass__new__, args_s)
            functions[klass__new__] = True
            function_values[klass, '__new__'] = klass__new__

        _, _, access_set = access_sets.find(klasses[0])
        for klass in klasses[1:]:
            _, _, access_set = access_sets.union(klasses[0], klass)
        if '__new__' in access_set.attrs:
            raise TyperError("PBC access set for classes %r already contains "
                             "a __new__" % (klasses,))
        access_set.attrs['__new__'] = annmodel.SomePBC(functions)
        access_set.values.update(function_values)

        # make a call family for 'functions', copying the call family for
        # 'klasses'
        functionslist = functions.keys()
        key0 = None, functionslist[0]
        _, _, new_call_family = call_families.find(key0)
        for klass__new__ in functionslist[1:]:
            _, _, new_call_family = call_families.union(key0,
                                                        (None, klass__new__))
        new_call_family.patterns = family.patterns


def perform_normalizations(rtyper):
    create_class_constructors(rtyper)
    rtyper.annotator.frozen += 1
    try:
        normalize_function_signatures(rtyper.annotator)
        specialize_pbcs_by_memotables(rtyper.annotator) 
        merge_classpbc_getattr_into_classdef(rtyper)
    finally:
        rtyper.annotator.frozen -= 1
