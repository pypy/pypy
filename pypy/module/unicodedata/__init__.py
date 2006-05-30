from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'unidata_version' : 'space.wrap(function.ucd.version)',
        'ucd_3_2_0'       : 'space.wrap(function.ucd_3_2_0)',
        'ucd_4_1_0'       : 'space.wrap(function.ucd_4_1_0)',
        'ucd'             : 'space.wrap(function.ucd)',
        '__doc__'         : "space.wrap('unicode character database')",
    }
    for name in '''lookup name decimal digit numeric category bidirectional
                   east_asian_width combining mirrored decomposition
                   normalize'''.split():
        interpleveldefs[name] = '''space.getattr(space.wrap(function.ucd),
                                   space.wrap("%s"))''' % name
