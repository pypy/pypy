import os
from pypy.interpreter.pyparser import parser, pytoken, metaparser

class PythonGrammar(parser.Grammar):

    KEYWORD_TOKEN = pytoken.python_tokens["NAME"]
    TOKENS = pytoken.python_tokens
    OPERATOR_MAP = pytoken.python_opmap

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
python_grammar_no_print = python_grammar.shared_copy()
python_grammar_no_print.keyword_ids = python_grammar_no_print.keyword_ids.copy()
del python_grammar_no_print.keyword_ids["print"]

class _Tokens(object):
    pass
for tok_name, idx in pytoken.python_tokens.iteritems():
    setattr(_Tokens, tok_name, idx)
tokens = _Tokens()

class _Symbols(object):
    pass
for sym_name, idx in python_grammar.symbol_ids.iteritems():
    setattr(_Symbols, sym_name, idx)
syms = _Symbols()

del _get_python_grammar, _Tokens, tok_name, sym_name, idx
