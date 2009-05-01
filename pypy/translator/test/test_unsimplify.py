import os
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.unsimplify import split_block, call_final_function
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy.rlib.objectmodel import we_are_translated
from pypy.tool.udir import udir

def translate(func, argtypes, type_system="lltype"):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper(type_system=type_system).specialize()
    return graphof(t, func), t

def test_split_blocks_simple():
    for i in range(4):
        def f(x, y):
            z = x + y
            w = x * y
            return z + w
        graph, t = translate(f, [int, int])
        split_block(t.annotator, graph.startblock, i)
        checkgraph(graph)
        interp = LLInterpreter(t.rtyper)
        result = interp.eval_graph(graph, [1, 2])
        assert result == 5
    
def test_split_blocks_conditional():
    for i in range(3):
        def f(x, y):
            if x + 12:
                return y + 1
            else:
                return y + 2
        graph, t = translate(f, [int, int])
        split_block(t.annotator, graph.startblock, i)
        checkgraph(graph)
        interp = LLInterpreter(t.rtyper)
        result = interp.eval_graph(graph, [-12, 2])
        assert result == 4
        result = interp.eval_graph(graph, [0, 2])
        assert result == 3

def test_split_block_exceptions():
    for i in range(2):
        def raises(x):
            if x == 1:
                raise ValueError
            elif x == 2:
                raise KeyError
            return x
        def catches(x):
            try:
                y = x + 1
                raises(y)
            except ValueError:
                return 0
            except KeyError:
                return 1
            return x
        graph, t = translate(catches, [int])
        split_block(t.annotator, graph.startblock, i)
        checkgraph(graph)
        interp = LLInterpreter(t.rtyper)
        result = interp.eval_graph(graph, [0])
        assert result == 0
        result = interp.eval_graph(graph, [1])
        assert result == 1
        result = interp.eval_graph(graph, [2])
        assert result == 2
    
def test_call_final_function():
    tmpfile = str(udir.join('test_call_final_function'))
    for type_system in ['lltype', 'ootype']:
        def f(x):
            return x * 6
        def goodbye_world():
            if we_are_translated():
                fd = os.open(tmpfile, os.O_WRONLY | os.O_CREAT, 0)
                os.close(fd)
        graph, t = translate(f, [int], type_system)
        call_final_function(t, goodbye_world)
        #
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)
        interp = LLInterpreter(t.rtyper)
        result = interp.eval_graph(graph, [7])
        assert result == 42
        assert os.path.isfile(tmpfile)
