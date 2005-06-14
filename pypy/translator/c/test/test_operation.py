import autopath
from pypy.objspace.flow.model import *
from pypy.objspace.flow.operation import FunctionByName
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler
from pypy.translator.translator import Translator

# XXX this tries to make compiling faster for full-scale testing
from pypy.translator.tool import buildpyxmodule
buildpyxmodule.enable_fast_compilation()


TESTCASES = [
    ('is_',             [], []),
    ('id',              False),
    ('id',              True),
    ('type',            42),
    ('issubtype',       bool, int),
    ('issubtype',       int, int),
    ('issubtype',       int, bool),
    ('repr',            'hi'),
    ('repr',            42),
    ('str',             'hi'),
    ('str',             42),
    ('len',             [1,3,5,7]),
    ('len',             'hello world'),
    ('hash',            'hello world'),
    ('pos',             42),
    ('neg',             42),
    ('nonzero',         42),
    ('abs' ,            -42),
    ('hex',             42),
    ('oct',             42),
    ('ord',             '*'),
    ('invert',          42),
    ('add',             40, 2),
    ('add',             'hello ', 'world'),
    ('add',             [1,3,5], [2,4]),
    ('sub',             40, 2),
    ('mul',             6, 7),
    ('mul',             [5], 4),
    ('mul',             5, [4]),
    ('truediv',         7, 2),
    ('floordiv',        7, 2),
    ('div',             7, 2),
    ('mod',             7, 2),
    ('divmod',          7, 2),
    ('pow',             5, 2, 7),
    ('lshift',          21, 1),
    ('rshift',          21, 1),
    ('and_',            21, 7),
    ('or_',             21, 7),
    ('xor',             21, 7),
    ('int',             42.5),
    ('float',           42),
    ('inplace_add',     'hello ', 'world'),
    ('inplace_sub',     32, 49),
    ('inplace_mul',     41, 12),
    ('inplace_truediv', 965, 22),
    ('inplace_floordiv',847, 31),
    ('inplace_div',     984, 12),
    ('inplace_mod',     148, 20),
    ('inplace_pow',     10, 6),
    ('inplace_lshift',  9148, 3),
    ('inplace_rshift',  1029, 2),
    ('inplace_and',     18711, 98172),
    ('inplace_or',      8722, 19837),
    ('inplace_xor',     91487, 18320),
    ('lt',              5, 7),
    ('lt',              5, 5),
    ('lt',              'hello', 'world'),
    ('le',              5, 7),
    ('le',              5, 5),
    ('le',              'hello', 'world'),
    ('eq',              5, 7),
    ('eq',              5, 5),
    ('eq',              'hello', 'world'),
    ('ne',              5, 7),
    ('ne',              5, 5),
    ('ne',              'hello', 'world'),
    ('gt',              5, 7),
    ('gt',              5, 5),
    ('gt',              'hello', 'world'),
    ('ge',              5, 7),
    ('ge',              5, 5),
    ('ge',              'hello', 'world'),
    ('cmp',             5, 7),
    ('cmp',             5, 5),
    ('cmp',             'hello', 'world'),
    ('contains',        [1,3,5,7], 4),
    ('contains',        [1,3,5,7], 5),
    ]

def operationtestfn():
    pass


class TestOperations:
    objspacename = 'flow'

    def build_cfunc(self, graph):
        t = Translator()
        t.entrypoint = operationtestfn
        t.functions.append(operationtestfn)
        t.flowgraphs[operationtestfn] = graph
        return skip_missing_compiler(t.ccompile)

    def test_operations(self):
        expected = []
        resvars = []
        block = Block([])
        for testcase in TESTCASES:
            opname = testcase[0]
            args = testcase[1:]
            op = SpaceOperation(opname, [Constant(x) for x in args], Variable())
            block.operations.append(op)
            expected.append(FunctionByName[opname](*args))
            resvars.append(op.result)
        op = SpaceOperation('newtuple', resvars, Variable())
        block.operations.append(op)
        graph = FunctionGraph('operationtestfn', block)
        block.closeblock(Link([op.result], graph.returnblock))

        fn = self.build_cfunc(graph)
        results = fn()

        assert len(results) == len(TESTCASES)
        for testcase, expected, result in zip(TESTCASES, expected, results):
            assert (type(expected) == type(result) and expected == result), (
                "%s(%s) computed %r instead of %r" % (
                testcase[0], ', '.join([repr(x) for x in testcase[1:]]),
                result, expected))
