import py

from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    "Python wrapper for Expat parser."

    appleveldefs = {
        'ExpatError' : 'app_pyexpat.ExpatError',
        'error'      : 'app_pyexpat.ExpatError',
        }

    interpleveldefs = {
        'ParserCreate':  'interp_pyexpat.ParserCreate',
        'XMLParserType': 'interp_pyexpat.W_XMLParserType',
        'ErrorString':   'interp_pyexpat.ErrorString',
        }

    for name in ['XML_PARAM_ENTITY_PARSING_NEVER',
                 'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
                 'XML_PARAM_ENTITY_PARSING_ALWAYS']:
        interpleveldefs[name] = 'space.wrap(interp_pyexpat.%s)' % (name,)

