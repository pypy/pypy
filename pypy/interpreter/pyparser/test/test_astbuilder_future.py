from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pyparser.grammar import Parser
from pypy.interpreter.pyparser.pytoken import setup_tokens
from fakes import FakeSpace


class ParserStub():
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


class TestBuilderFuture:
    def setup_class(self):
        self.parser = ParserStub()
        setup_tokens(self.parser)

    def setup_method(self, method):
        self.builder = AstBuilder(self.parser, space=FakeSpace())

    def test_future_rules(self):
        assert 'future_import_feature' in self.builder.build_rules
