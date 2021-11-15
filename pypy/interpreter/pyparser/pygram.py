import os
from pypy.interpreter.pyparser import parser, pytoken, metaparser

class PythonGrammar(parser.Grammar):

    KEYWORD_TOKEN = pytoken.python_tokens["NAME"]
    TOKENS = pytoken.python_tokens
    OPERATOR_MAP = pytoken.python_opmap

    def classify(self, token):
        """Find the label for a token."""
        if token.token_type == self.KEYWORD_TOKEN:
            label_index = self.keyword_ids.get(token.value, -1)
            if label_index != -1:
                return label_index
        label_index = token.token_type
        if label_index == -1 or (label_index == tokens.REVDBMETAVAR and not self.revdb):
            raise ParseError("invalid token", token)
        return label_index

def _get_python_grammar():
    here = os.path.dirname(__file__)
    fp = open(os.path.join(here, "data", "Grammar2.7"))
    try:
        gram_source = fp.read()
    finally:
        fp.close()
    pgen = metaparser.ParserGenerator(gram_source)
    return pgen.build_grammar(PythonGrammar)


python_grammar = _get_python_grammar()
python_grammar.revdb = False
python_grammar_no_print = python_grammar.shared_copy()
python_grammar_no_print.revdb = False
python_grammar_no_print.keyword_ids = python_grammar_no_print.keyword_ids.copy()
del python_grammar_no_print.keyword_ids["print"]

python_grammar_revdb = python_grammar.shared_copy()
python_grammar_revdb.revdb = True
python_grammar_no_print_revdb = python_grammar_no_print.shared_copy()
python_grammar_no_print_revdb.revdb = True


class _Tokens(object):
    pass
for tok_name, idx in pytoken.python_tokens.iteritems():
    setattr(_Tokens, tok_name, python_grammar.token_ids.get(idx, -1))
    if tok_name == "NAME":
        PythonGrammar.KEYWORD_TOKEN = python_grammar.token_ids[idx]
tokens = _Tokens()

python_opmap = {}
for op, idx in pytoken.python_opmap.iteritems():
    python_opmap[op] = python_grammar.token_ids.get(idx, -1)

class _Symbols(object):
    pass
rev_lookup = {}
for sym_name, idx in python_grammar.symbol_ids.iteritems():
    setattr(_Symbols, sym_name, idx)
    rev_lookup[idx] = sym_name
syms = _Symbols()
syms._rev_lookup = rev_lookup # for debugging

del _get_python_grammar, _Tokens, tok_name, sym_name, idx

def choose_grammar(print_function, revdb):
    if print_function:
        if revdb:
            return python_grammar_no_print_revdb
        else:
            return python_grammar_no_print
    else:
        if revdb:
            return python_grammar_revdb
        else:
            return python_grammar

