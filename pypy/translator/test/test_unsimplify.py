from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.translator import Translator
from pypy.translator.unsimplify import split_block

def test_split_blocks_simple():
    for i in range(4):
        def f(x, y):
            z = x + y
            w = x * y
            return z + w
        t = Translator(f)
        a = t.annotate([int, int])
        t.specialize()
        graph = t.flowgraphs[f]
        split_block(t, graph, graph.startblock, i)
        interp = LLInterpreter(t.flowgraphs, t.rtyper)
        result = interp.eval_function(f, [1, 2])
        assert result == 5
    
def test_split_blocks_conditional():
    for i in range(3):
        def f(x, y):
            if x + 12:
                return y + 1
            else:
                return y + 2
        t = Translator(f)
        a = t.annotate([int, int])
        t.specialize()
        graph = t.flowgraphs[f]
        split_block(t, graph, graph.startblock, i)
        interp = LLInterpreter(t.flowgraphs, t.rtyper)
        result = interp.eval_function(f, [-12, 2])
        assert result == 4
        result = interp.eval_function(f, [0, 2])
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
        t = Translator(catches)
        a = t.annotate([int])
        t.specialize()
        graph = t.flowgraphs[catches]
        split_block(t, graph, graph.startblock, i)
        interp = LLInterpreter(t.flowgraphs, t.rtyper)
        result = interp.eval_function(catches, [0])
        assert result == 0
        result = interp.eval_function(catches, [1])
        assert result == 1
        result = interp.eval_function(catches, [2])
        assert result == 2
    
