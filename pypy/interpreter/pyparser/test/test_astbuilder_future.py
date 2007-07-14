from pypy.interpreter.astcompiler import consts
from pypy.interpreter.pyparser.grammar import Parser
from pypy.interpreter.pyparser.pytoken import setup_tokens
from pypy.interpreter.pyparser import astbuilder
from pypy.interpreter.pyparser.asthelper import TokenObject

from fakes import FakeSpace


class ParserStub:
    def __init__(self):
        self.tokens = {}
        self._sym_count = 0
        self.tok_values = {}
        self.tok_rvalues = {}
        self.trace = []

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

    def add_production(self, rule):
        self.trace.append(rule)

class RuleStub:
    def __init__(self, name, root=False):
        self.codename = name
        self.root = root
    is_root = lambda self: self.root


class TokenForTest(TokenObject):
    def __init__(self, value, parser):
        TokenObject.__init__(self, 'dummy', value, -1, parser)


class FakeSpaceForFeatureLookup(FakeSpace):
    feature_code_lookup = {'with_statement': consts.CO_FUTURE_WITH_STATEMENT}
    def appexec(self, posargs_w, code):
        feature_name = posargs_w[0]
        return self.feature_code_lookup.get(feature_name, 0)


class TestBuilderFuture:
    def setup_class(self):
        self.parser = ParserStub()
        setup_tokens(self.parser)

    def setup_method(self, method):
        self.builder = astbuilder.AstBuilder(
            self.parser, space=FakeSpaceForFeatureLookup(),
            grammar_version="2.5a")

    def test_future_rules(self):
        assert (self.builder.build_rules['future_import_feature'] is
                astbuilder.build_future_import_feature)
        assert (self.builder.build_rules['import_from_future'] is
                astbuilder.build_import_from)

    def test_future_import(self):
        token_values = ['with_statement', 'as', 'stuff']
        for val in token_values:
            self.builder.push(TokenForTest(val, self.parser))

        astbuilder.build_future_import_feature(self.builder, len(token_values))
        assert ([rule.value for rule in self.builder.rule_stack] ==
                token_values)
        assert self.parser.trace == [32768]

