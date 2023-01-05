import os
from pypy.interpreter.pyparser import pytoken

class _Tokens(object):
    pass
for tok_name, idx in pytoken.python_tokens.iteritems():
    setattr(_Tokens, tok_name, idx)
tokens = _Tokens()

