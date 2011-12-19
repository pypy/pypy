from pypy.conftest import option
from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.objspace.flow.model import Variable
from pypy.translator.translator import TranslationContext
from pypy.translator.generator import replace_graph_with_bootstrap
from pypy.translator.generator import get_variable_names


# ____________________________________________________________

def f_gen(n):
    i = 0
    while i < n:
        yield i
        i += 1

class GeneratorIterator(object):
    def __init__(self, entry):
        self.current = entry
    def next(self):
        e = self.current
        self.current = None
        if isinstance(e, Yield1):
            n = e.n_0
            i = e.i_0
            i += 1
        else:
            n = e.n_0
            i = 0
        if i < n:
            e = Yield1()
            e.n_0 = n
            e.i_0 = i
            self.current = e
            return i
        raise StopIteration

    def __iter__(self):
        return self

class AbstractPosition(object):
    _immutable_ = True
class Entry1(AbstractPosition):
    _immutable_ = True
class Yield1(AbstractPosition):
    _immutable_ = True

def f_explicit(n):
    e = Entry1()
    e.n_0 = n
    return GeneratorIterator(e)

def test_explicit():
    assert list(f_gen(10)) == list(f_explicit(10))

def test_get_variable_names():
    lst = get_variable_names([Variable('a'), Variable('b_'), Variable('a')])
    assert lst == ['g_a', 'g_b', 'g_a_']

# ____________________________________________________________


class TestGenerator:

    def test_replace_graph_with_bootstrap(self):
        def func(n, x, y, z):
            yield n
            yield n
        #
        space = FlowObjSpace()
        graph = space.build_flow(func)
        assert graph.startblock.operations[0].opname == 'generator_mark'
        replace_graph_with_bootstrap(graph, 'newgraph')
        if option.view:
            graph.show()
        block = graph.startblock
        ops = block.operations
        assert ops[0].opname == 'call'      # e = Entry1()
        assert ops[1].opname == 'setattr'   # e.g_n = n
        assert ops[1].args[1].value == 'g_n'
        assert ops[2].opname == 'setattr'   # e.g_x = x
        assert ops[2].args[1].value == 'g_x'
        assert ops[3].opname == 'setattr'   # e.g_y = y
        assert ops[3].args[1].value == 'g_y'
        assert ops[4].opname == 'setattr'   # e.g_z = z
        assert ops[4].args[1].value == 'g_z'
        assert ops[5].opname == 'call'      # g = GeneratorIterator(e)
        assert ops[5].args[1] == ops[0].result
        assert len(ops) == 6
        assert len(block.exits) == 1
        assert block.exits[0].target is graph.returnblock

    def test_make_generator_body_graph(self):
        def f(n, x, y, z):
            z *= 10
            yield n
            z -= 10
        #
        def f__next(generator):
            n = generator.n_0
            x = generator.x_0
            y = generator.y_0
            z = generator.z_0
            e = generator.current
            generator.current = None
            if isinstance(e, "some class"):
                xxx
        #
        space = FlowObjSpace()
        graph = space.build_flow(func)
        newgraph = make_generator_body_graph(graph)
        assert len(newgraph.startblock.inputargs) == 1
        [v_generator] = newgraph.startblock.inputargs
        ops = newgraph.startblock.operations
        assert ops[0].opname == 'getattr'   # n = g.n_0
        assert ops[0].args[0] == v_generator
        assert ops[0].args[1].value.startswith('n_')
        assert ops[1].opname == 'getattr'   # x = g.x_0
        assert ops[1].args[0] == v_generator
        assert ops[1].args[1].value.startswith('x_')
        assert ops[2].opname == 'getattr'   # y = g.y_0
        assert ops[2].args[0] == v_generator
        assert ops[2].args[1].value.startswith('y_')
        assert ops[3].opname == 'getattr'   # z = g.z_0
        assert ops[3].args[0] == v_generator
        assert ops[3].args[1].value.startswith('z_')
        assert ops[4].opname == 'getattr'   # e = g.current
        assert ops[4].args[0] == v_generator
        assert ops[4].args[1].value == 'current'
        assert ops[5].opname == 'setattr'   # g.current = None
        assert ops[5].args[0] == v_generator
        assert ops[5].args[1].value == 'current'
        assert ops[6].opname == 'call'      # isinstance(e, Yield1)
        assert ops[6].args[0].value == isinstance
        assert len(ops) == 7
