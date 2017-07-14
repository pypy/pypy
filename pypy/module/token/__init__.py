from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.pyparser import pytoken, pygram


class Module(MixedModule):

    appleveldefs = {}
    interpleveldefs = {
        "NT_OFFSET" : "space.newint(256)",
        "ISTERMINAL" : "__init__.isterminal",
        "ISNONTERMINAL" : "__init__.isnonterminal",
        "ISEOF" : "__init__.iseof"
        }


def _init_tokens():
    tok_name = {}
    for tok, id in pytoken.python_tokens.iteritems():
        Module.interpleveldefs[tok] = "space.wrap(%d)" % (id,)
        tok_name[id] = tok
    Module.interpleveldefs["tok_name"] = "space.wrap(%r)" % (tok_name,)
    Module.interpleveldefs["N_TOKENS"] = "space.wrap(%d)" % len(tok_name)
    all_names = Module.interpleveldefs.keys()
    # obscure, but these names are not in CPython's token module
    # so we remove them from 'token.__all__' otherwise they end up
    # twice in 'tokenize.__all__'
    all_names.remove('COMMENT')
    all_names.remove('NL')
    Module.interpleveldefs["__all__"] = "space.wrap(%r)" % (all_names,)

_init_tokens()


@unwrap_spec(tok=int)
def isterminal(space, tok):
    return space.newbool(tok < 256)

@unwrap_spec(tok=int)
def isnonterminal(space, tok):
    return space.newbool(tok >= 256)

@unwrap_spec(tok=int)
def iseof(space, tok):
    return space.newbool(tok == pygram.tokens.ENDMARKER)
