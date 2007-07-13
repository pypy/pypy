from pypy.interpreter.pyparser.grammar import Parser
from pypy.interpreter.pyparser.pytoken import setup_tokens
from pypy.interpreter.pyparser import astbuilder

from fakes import FakeSpace


class ParserStub:
    def __init__(self):
        self.tokens = {}
        self._sym_count = 0
        self.tok_values = {}
        self.tok_rvalues = {}

    def add_token( self, tok, value = None ):
        # assert isinstance( tok, str )
        if not tok in self.tokens:
            val = self._sym_count
            self._sym_count += 1
            self.tokens[tok] = val
            #self.tok_name[val] = tok
            if value is not None:
                self.tok_values[value] = val
                self.tok_rvalues[val] = value
            return val
        return self.tokens[ tok ]


class RuleStub:
    def __init__(self, name, root=False):
        self.codename = name
        self.root = root
    is_root = lambda self: self.root


class TestBuilderFuture:
    def setup_class(self):
        self.parser = ParserStub()
        setup_tokens(self.parser)

    def setup_method(self, method):
        self.builder = astbuilder.AstBuilder(self.parser, space=FakeSpace())

    def test_future_rules(self):
        assert (self.builder.build_rules['future_import_feature'] is
                astbuilder.build_future_import_feature)
        assert (self.builder.build_rules['import_from_future'] is
                astbuilder.build_import_from)

    def test_future_import(self):
        #self.builder.push(RuleStub('future_import_feature', root=True))
        pass
