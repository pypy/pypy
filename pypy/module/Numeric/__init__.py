from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """An RPython reimplementation of the Numeric module
"""

    appleveldefs = {
    }

    interpleveldefs = {
        'Float' : "space.wrap('d')",
        'Int' : "space.wrap('l')",
#        'array' : 'interp_numeric.w_array',
        'zeros' : 'interp_numeric.w_zeros',
        'array'  : 'interp_numeric.array',
        'ArrayType' : 'space.gettypeobject(interp_numeric.W_Array.typedef)',
        'TOWER_TYPES' : 'space.wrap(interp_numeric.TOWER_TYPES)',
        'TOWER_TYPES_VALUES' :'space.wrap(interp_numeric.TOWER_TYPES_VALUES)'
        }

##         'CODESIZE':       'space.wrap(interp_sre.CODESIZE)',
##         'MAGIC':          'space.wrap(interp_sre.MAGIC)',
##         'copyright':      'space.wrap(interp_sre.copyright)',
##         'getlower':       'interp_sre.w_getlower',
##         'getcodesize':    'interp_sre.w_getcodesize',
##         '_State':         'interp_sre.make_state',
##         '_match':         'interp_sre.w_match',
##         '_search':        'interp_sre.w_search',
