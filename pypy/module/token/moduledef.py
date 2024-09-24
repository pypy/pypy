from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.pyparser import pytoken


class Module(MixedModule):

    appleveldefs = {}
    interpleveldefs = {
        "NT_OFFSET" : "space.newint(256)",
        "ISTERMINAL" : "interp_token.isterminal",
        "ISNONTERMINAL" : "interp_token.isnonterminal",
        "ISEOF" : "interp_token.iseof"
        }


def _init_tokens():
    tok_name = {}
    for tok, id in pytoken.python_tokens.iteritems():
        Module.interpleveldefs[tok] = "space.wrap(%d)" % (id,)
        tok_name[id] = tok
    Module.interpleveldefs["tok_name"] = "space.wrap(%r)" % (tok_name,)
    Module.interpleveldefs["N_TOKENS"] = "space.wrap(%d)" % len(tok_name)
    exact_token_types = pytoken.python_opmap.copy()
    del exact_token_types['<>'] # only for barry_as_FLUFL, not exposed in token
    Module.interpleveldefs['EXACT_TOKEN_TYPES'] = "space.wrap(%r)" % exact_token_types
    all_names = Module.interpleveldefs.keys()
    Module.interpleveldefs["__all__"] = "space.wrap(%r)" % (all_names,)


_init_tokens()
