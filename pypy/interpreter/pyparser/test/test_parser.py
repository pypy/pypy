from pypy.interpreter.pyparser.grammar import Parser
from pypy.interpreter.pyparser import error

def test_symbols():
    p = Parser()
    x1 = p.add_symbol('sym')
    x2 = p.add_token('tok')
    x3 = p.add_anon_symbol(':sym')
    x4 = p.add_anon_symbol(':sym1')
    # test basic numbering assumption
    # symbols and tokens are attributed sequentially
    # using the same counter
    assert x2 == x1 + 1
    # anon symbols have negative value
    assert x3 != x2 + 1
    assert x4 == x3 - 1
    assert x3 < 0
    y1 = p.add_symbol('sym')
    assert y1 == x1
    y2 = p.add_token('tok')
    assert y2 == x2
    y3 = p.add_symbol(':sym')
    assert y3 == x3
    y4 = p.add_symbol(':sym1')
    assert y4 == x4


def test_load():
    d = { 5 : 'sym1',
          6 : 'sym2',
          9 : 'sym3',
          }
    p = Parser()
    p.load_symbols( d )
    v = p.add_symbol('sym4')
    # check that we avoid numbering conflicts
    assert v>9
    v = p.add_symbol( 'sym1' )
    assert v == 5
    v = p.add_symbol( 'sym2' )
    assert v == 6
    v = p.add_symbol( 'sym3' )
    assert v == 9

class FakeSpace:
    w_None = None
    w_str = str
    w_basestring = basestring
    w_int = int
    
    def wrap(self,obj):
        return obj

    def isinstance(self, obj, wtype ):
        return isinstance(obj,wtype)

    def is_true(self, obj):
        return obj

    def eq_w(self, obj1, obj2):
        return obj1 == obj2

    def is_w(self, obj1, obj2):
        return obj1 is obj2

    def type(self, obj):
        return type(obj)

    def newlist(self, lst):
        return list(lst)

    def newtuple(self, lst):
        return tuple(lst)
    
    def call_method(self, obj, meth, *args):
        return getattr(obj, meth)(*args)

    def call_function(self, func, *args):
        return func(*args)

    builtin = dict(int=int, long=long, float=float, complex=complex)

from pypy.interpreter.pyparser.asthelper import get_atoms
class RuleTracer(dict):
    
    def __init__(self, *args, **kw):
        self.trace = []

    def __getitem__(self, attr):
        if attr in ['dotted_name', 'dotted_as_name', 'dotted_as_names',
                    'import_stmt', 'small_stmt', 'simple_stmt', 'stmt',
                    'single_input', 'file_input', 'future_import_list',
                    'import_from_future', 'future_import_as_names']:
            return None
        
        def record_trace(builder, number):
            result = [t.value for t in get_atoms(builder, number)]
            self.trace.append((attr, result))
        return record_trace

    def get(self, attr, default):
        return self.__getitem__(attr)
    
from pypy.interpreter.pyparser.astbuilder import AstBuilder
class MockBuilder(AstBuilder):

    def __init__(self, *args, **kw):
        AstBuilder.__init__(self, *args, **kw)
        self.build_rules = RuleTracer()


class TestFuture(object):
    
    def setup_class(self):
        from pypy.interpreter.pyparser.pythonparse import make_pyparser
        self.parser = make_pyparser('2.5a')

    def setup_method(self, method):
        self.builder = MockBuilder(self.parser, space=FakeSpace())

    def check_parse_mode(self, tst, expected, mode):
        self.parser.parse_source(tst, mode, self.builder)
        assert self.builder.build_rules.trace == expected
        
    def check_parse(self, tst, expected):
        self.check_parse_mode(tst, expected, 'exec')
        self.builder.build_rules.trace = []
        self.check_parse_mode(tst, expected, 'single')

        
    def test_single_future_import(self):
        tst = 'from __future__ import na\n'
        expected = [('future_import_feature', ['na'])]
        self.check_parse(tst, expected)
        
    def test_double_future_import(self):
        tst = 'from __future__ import na, xx\n'
        expected = [('future_import_feature', ['na']),
                    ('future_import_feature', ['xx'])]
        self.check_parse(tst, expected)

    def test_two_future_imports(self):
        tst = 'from __future__ import na;from __future__ import xx\n'
        expected = [('future_import_feature', ['na']),
                    ('future_import_feature', ['xx'])]
        self.check_parse(tst, expected)

    def test_future_imports_nl(self):
        tst = '''
from __future__ import na
from __future__ import xx;
from __future__ import yy
'''
        expected = [('future_import_feature', ['na']),
                    ('future_import_feature', ['xx']),
                    ('future_import_feature', ['yy'])]
        self.check_parse_mode(tst, expected,'exec')

    def test_single_future_as(self):
        tst = 'from __future__ import na as x\n'
        expected = [('future_import_feature', ['na', 'as', 'x'])]
        self.check_parse(tst, expected)
        
    def test_single_future_as(self):
        tst = 'import sys;from __future__ import na as x\n'
        expected = []
        try:
            self.check_parse_mode(tst, expected,'exec')
            assert False == 'An import before a future import should throw an error.'
        except error.SyntaxError:
            pass

    def test_regular_import(self):
        tst = 'import sys'
        expected = [('import_name', ['import', 'sys'])]
        self.check_parse(tst, expected)
        
