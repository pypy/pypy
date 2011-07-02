import py

from pypy.interpreter.mixedmodule import MixedModule

class ErrorsModule(MixedModule):
    "Definition of pyexpat.errors module."

    appleveldefs = {
        }

    interpleveldefs = {
        }

    def setup_after_space_initialization(self):
        from pypy.module.pyexpat import interp_pyexpat
        for name in interp_pyexpat.xml_error_list:
            self.space.setattr(self, self.space.wrap(name),
                    interp_pyexpat.ErrorString(self.space,
                    getattr(interp_pyexpat, name)))

class Module(MixedModule):
    "Python wrapper for Expat parser."

    appleveldefs = {
        }

    interpleveldefs = {
        'ParserCreate':  'interp_pyexpat.ParserCreate',
        'XMLParserType': 'interp_pyexpat.W_XMLParserType',
        'ErrorString':   'interp_pyexpat.ErrorString',

        'ExpatError':    'space.fromcache(interp_pyexpat.Cache).w_error',
        'error':         'space.fromcache(interp_pyexpat.Cache).w_error',

        '__version__':   'space.wrap("85819")',
        'EXPAT_VERSION': 'interp_pyexpat.get_expat_version(space)',
        'version_info':  'interp_pyexpat.get_expat_version_info(space)',
        }

    submodules = {
        'errors': ErrorsModule,
    }

    for name in ['XML_PARAM_ENTITY_PARSING_NEVER',
                 'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
                 'XML_PARAM_ENTITY_PARSING_ALWAYS']:
        interpleveldefs[name] = 'space.wrap(interp_pyexpat.%s)' % (name,)

