#!/usr/bin/env python
"""This module loads the python Grammar (2.3, 2.4 or 2.5)

helper functions are provided that use the grammar to parse
using file_input, single_input and eval_input targets
"""
from pypy.interpreter import gateway
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.interpreter.pyparser.pythonlexer import Source, match_encoding_declaration
from pypy.interpreter.astcompiler.consts import CO_FUTURE_WITH_STATEMENT
import pypy.interpreter.pyparser.pytoken as pytoken
import pypy.interpreter.pyparser.ebnfparse as ebnfparse
from pypy.interpreter.pyparser.ebnflexer import GrammarSource
from pypy.interpreter.pyparser.ebnfgrammar import GRAMMAR_GRAMMAR
import pypy.interpreter.pyparser.grammar as grammar
from pypy.interpreter.pyparser.pythonutil import build_parser_for_version
from pypy.interpreter.pyparser import symbol

from codeop import PyCF_DONT_IMPLY_DEDENT


##  files encoding management ############################################
_recode_to_utf8 = gateway.applevel(r'''
    def _recode_to_utf8(text, encoding):
        return unicode(text, encoding).encode("utf-8")
''').interphook('_recode_to_utf8')

def recode_to_utf8(space, text, encoding):
    return space.str_w(_recode_to_utf8(space, space.wrap(text),
                                          space.wrap(encoding)))
def _normalize_encoding(encoding):
    """returns normalized name for <encoding>

    see dist/src/Parser/tokenizer.c 'get_normal_name()'
    for implementation details / reference

    NOTE: for now, parser.suite() raises a MemoryError when
          a bad encoding is used. (SF bug #979739)
    """
    if encoding is None:
        return None
    # lower() + '_' / '-' conversion
    encoding = encoding.replace('_', '-').lower()
    if encoding.startswith('utf-8'):
        return 'utf-8'
    for variant in ['latin-1', 'iso-latin-1', 'iso-8859-1']:
        if encoding.startswith(variant):
            return 'iso-8859-1'
    return encoding

def _check_for_encoding(s):
    eol = s.find('\n')
    if eol < 0:
        return _check_line_for_encoding(s)
    enc = _check_line_for_encoding(s[:eol])
    if enc:
        return enc
    eol2 = s.find('\n', eol + 1)
    if eol2 < 0:
        return _check_line_for_encoding(s[eol + 1:])
    return _check_line_for_encoding(s[eol + 1:eol2])


def _check_line_for_encoding(line):
    """returns the declared encoding or None"""
    i = 0
    for i in range(len(line)):
        if line[i] == '#':
            break
        if line[i] not in ' \t\014':
            return None
    return match_encoding_declaration(line[i:])


## Python Source Parser ###################################################
class PythonParser(grammar.Parser):
    """Wrapper class for python grammar"""
    targets = {
        'eval' : "eval_input",
        'single' : "single_input",
        'exec' : "file_input",
        }

    def __init__(self): # , predefined_symbols=None):
        grammar.Parser.__init__(self)
        pytoken.setup_tokens(self)
        # remember how many tokens were loaded
        self._basetokens_count = self._sym_count
        # if predefined_symbols:
        #     self.load_symbols(predefined_symbols)
        self.keywords = []

    def is_base_token(self, tokvalue):
        return tokvalue < 0 or tokvalue >= self._basetokens_count

    def parse_source(self, textsrc, mode, builder, flags=0):
        """Parse a python source according to goal"""
        goal = self.targets[mode]
        # Detect source encoding.
        if textsrc[:3] == '\xEF\xBB\xBF':
            textsrc = textsrc[3:]
            enc = 'utf-8'
        else:
            enc = _normalize_encoding(_check_for_encoding(textsrc))
            if enc is not None and enc not in ('utf-8', 'iso-8859-1'):
                textsrc = recode_to_utf8(builder.space, textsrc, enc)

        lines = [line + '\n' for line in textsrc.split('\n')]
        builder.source_encoding = enc
        if len(textsrc) and textsrc[-1] == '\n':
            lines.pop()
            flags &= ~PyCF_DONT_IMPLY_DEDENT
        return self.parse_lines(lines, goal, builder, flags)


    def parse_lines(self, lines, goal, builder, flags=0):
        goalnumber = self.symbols[goal]
        target = self.root_rules[goalnumber]
        keywords = {} # dict.fromkeys(self.keywords)
        disable_with = not (flags & CO_FUTURE_WITH_STATEMENT)
        for keyword in self.keywords:
            if disable_with and keyword in ('with', 'as'):
                continue
            keywords[keyword] = None
        src = Source(self, lines, keywords, flags)

        if not target.match(src, builder):
            line, lineno = src.debug()
            # XXX needs better error messages
            raise SyntaxError("invalid syntax", lineno, -1, line)
            # return None
        return builder

    def update_rules_references(self):
        """update references to old rules"""
        # brute force algorithm
        for rule in self.all_rules:
            for i in range(len(rule.args)):
                arg = rule.args[i]
                if arg.codename in self.root_rules:
                    real_rule = self.root_rules[arg.codename]
                    # This rule has been updated
                    if real_rule is not rule.args[i]:
                        rule.args[i] = real_rule


    def insert_rule(self, ruledef):
        """parses <ruledef> and inserts corresponding rules in the parser"""
        # parse the ruledef(s)
        source = GrammarSource(GRAMMAR_GRAMMAR, ruledef)
        builder = ebnfparse.EBNFBuilder(GRAMMAR_GRAMMAR, dest_parser=self)
        GRAMMAR_GRAMMAR.root_rules['grammar'].match(source, builder)
        # remove proxy objects if any
        builder.resolve_rules()
        # update keywords
        self.keywords.extend(builder.keywords)
        # update old references in case an existing rule was modified
        self.update_rules_references()
        # recompute first sets
        self.build_first_sets()


def make_pyparser(version):
    parser = PythonParser()
    return build_parser_for_version(version, parser=parser)


def translation_target(grammardef):
    parser = PythonParser() # predefined_symbols=symbol.sym_name)
    source = GrammarSource(GRAMMAR_GRAMMAR, grammardef)
    builder = ebnfparse.EBNFBuilder(GRAMMAR_GRAMMAR, dest_parser=parser)
    GRAMMAR_GRAMMAR.root_rules['grammar'].match(source, builder)
    builder.resolve_rules()
    parser.build_first_sets()
    parser.keywords = builder.keywords
    return 0
