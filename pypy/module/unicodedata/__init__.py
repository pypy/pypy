from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'lookup'          : 'function.lookup',
        'name'            : 'function.name',
        'decimal'         : 'function.decimal',
        'digit'           : 'function.digit',
        'numeric'         : 'function.numeric',
        'category'        : 'function.category',
        'bidirectional'   : 'function.bidirectional',
        'east_asian_width': 'function.east_asian_width',
        'combining'       : 'function.combining',
        'mirrored'        : 'function.mirrored',
        'decomposition'   : 'function.decomposition',
        'normalize'       : 'function.normalize',
        'unidata_version' : 'space.wrap(unicodedb.version)',
        '__doc__'         : "space.wrap('unicode character database')",
    }
