from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import SpaceOperation, checkgraph
from pypy.annotation.model import *
from pypy.tool.sourcetools import has_varargs
from pypy.rpython.rmodel import TyperError


def normalize_function_signatures(annotator):
    # make sure that all functions called in a group have exactly
    # the same signature, by hacking their flow graphs if needed
    callables = annotator.getpbccallables()
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
    # find the most general signature of each family
    for family in call_families.infos():
        functions = [func for classdef, func in family.objects
                          if classdef is None]  # ignore methods now
        if len(functions) > 1:  # otherwise, nothing to do
            if len(family.patterns) > 1:
                raise TyperError("don't support multiple call patterns "
                                 "to multiple functions for now %r" % (
                    functions))
            pattern, = family.patterns
            shape_cnt, shape_keys, shape_star, shape_stst = pattern
            assert not shape_keys, "XXX not implemented"
            assert not shape_star, "XXX not implemented"
            assert not shape_stst, "XXX not implemented"
            # for the first 'shape_cnt' arguments we need to generalize to
            # a common type
            generalizedargs = []
            graph_bindings = {}
            default_values = {}
            for func in functions:
                assert not has_varargs(func), "XXX not implemented"
                graph = annotator.translator.getflowgraph(func)
                graph_bindings[graph] = [annotator.binding(v)
                                         for v in graph.getargs()]
            for i in range(shape_cnt):
                args_s = []
                for bindings in graph_bindings.values():
                    args_s.append(bindings[i])
                s_value = unionof(*args_s)
                generalizedargs.append(s_value)
            for func in functions:
                graph = annotator.translator.getflowgraph(func)
                bindings = graph_bindings[graph]
                if generalizedargs != bindings: #NB. bindings can also be longer
                    oldblock = graph.startblock
                    vlist = []
                    for i in range(len(generalizedargs)):
                        v = Variable(graph.getargs()[i])
                        annotator.setbinding(v, generalizedargs[i])
                        vlist.append(v)
                    newblock = Block(vlist)
                    # add the defaults as constants
                    defaults = func.func_defaults or ()
                    for i in range(len(generalizedargs), len(bindings)):
                        try:
                            default = defaults[i-len(bindings)]
                        except IndexError:
                            raise TyperError("call pattern has %d arguments, "
                                             "but %r takes at least %d "
                                             "arguments" % (
                                len(generalizedargs), func,
                                len(bindings) - len(defaults)))
                        vlist.append(Constant(default))
                    newblock.closeblock(Link(vlist, oldblock))
                    oldblock.isstartblock = False
                    newblock.isstartblock = True
                    graph.startblock = newblock
                    # finished
                    checkgraph(graph)
                    annotator.annotated[newblock] = annotator.annotated[oldblock]
                # XXX convert the return value too


def perform_normalizations(annotator):
    annotator.frozen += 1
    try:
        normalize_function_signatures(annotator)
    finally:
        annotator.frozen -= 1
