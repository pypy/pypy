from pypy.interpreter.mixedmodule import MixedModule

# This is the default unicodedb used in various places:
# - the unicode type
# - the regular expression engine
from pypy.module.unicodedata.interp_ucd import ucd as _ucd
unicodedb = _ucd._unicodedb

# to get information about individual unicode chars look at:
# http://www.fileformat.info/info/unicode/char/search.htm

class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
        'unidata_version' : 'space.wrap(interp_ucd.ucd.version)',
        'ucd_3_2_0'       : 'space.wrap(interp_ucd.ucd_3_2_0)',
        'ucd_8_0_0'       : 'space.wrap(interp_ucd.ucd_8_0_0)',
        'ucd'             : 'space.wrap(interp_ucd.ucd)',
        '__doc__'         : "space.wrap('unicode character database')",
    }
    for name in '''lookup name decimal digit numeric category bidirectional
                   east_asian_width combining mirrored decomposition
                   normalize _get_code'''.split():
        interpleveldefs[name] = '''space.getattr(space.wrap(interp_ucd.ucd),
                                   space.wrap("%s"))''' % name
