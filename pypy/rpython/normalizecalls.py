import types
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

    # for classes that appear in families, unify their __init__ as well.
    for family in call_families.infos():
        prevkey = None
        for _, klass in family.objects:
            if isinstance(klass, (type, types.ClassType)):
                try:
                    initfunc = klass.__init__.im_func
                except AttributeError:
                    continue
                if prevkey is None:
                    prevkey = (None, initfunc)
                else:
                    call_families.union((None, initfunc), prevkey)

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
        #  - classes: their __init__ unbound methods are also families
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


def perform_normalizations(annotator):
    annotator.frozen += 1
    try:
        normalize_function_signatures(annotator)
    finally:
        annotator.frozen -= 1
