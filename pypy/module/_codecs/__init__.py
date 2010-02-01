from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib import runicode

class Module(MixedModule):
    appleveldefs = {
         '__doc__' :  'app_codecs.__doc__',
         '__name__' :  'app_codecs.__name__',
         'charmap_encode' :  'app_codecs.charmap_encode',
         'escape_decode' :  'app_codecs.escape_decode',
         'escape_encode' :  'app_codecs.escape_encode',
         'raw_unicode_escape_decode' :  'app_codecs.raw_unicode_escape_decode',
         'raw_unicode_escape_encode' :  'app_codecs.raw_unicode_escape_encode',
         'unicode_escape_decode' :  'app_codecs.unicode_escape_decode',
         'unicode_escape_encode' :  'app_codecs.unicode_escape_encode',
         'unicode_internal_decode' :  'app_codecs.unicode_internal_decode',
         'unicode_internal_encode' :  'app_codecs.unicode_internal_encode',
         'utf_7_decode' :  'app_codecs.utf_7_decode',
         'utf_7_encode' :  'app_codecs.utf_7_encode',
         '_register_existing_errors': 'app_codecs._register_existing_errors',
         'charmap_build' : 'app_codecs.charmap_build'
    }
    interpleveldefs = {
         'encode':         'interp_codecs.encode',
         'decode':         'interp_codecs.decode',
         'lookup':         'interp_codecs.lookup_codec',
         'lookup_error':   'interp_codecs.lookup_error',
         'register':       'interp_codecs.register_codec',
         'register_error': 'interp_codecs.register_error',

         # encoders and decoders
         'ascii_decode'     : 'interp_codecs.ascii_decode',
         'ascii_encode'     : 'interp_codecs.ascii_encode',
         'latin_1_decode'   : 'interp_codecs.latin_1_decode',
         'latin_1_encode'   : 'interp_codecs.latin_1_encode',
         'utf_8_decode'     : 'interp_codecs.utf_8_decode',
         'utf_8_encode'     : 'interp_codecs.utf_8_encode',
         'utf_16_be_decode' : 'interp_codecs.utf_16_be_decode',
         'utf_16_be_encode' : 'interp_codecs.utf_16_be_encode',
         'utf_16_decode'    : 'interp_codecs.utf_16_decode',
         'utf_16_encode'    : 'interp_codecs.utf_16_encode',
         'utf_16_le_decode' : 'interp_codecs.utf_16_le_decode',
         'utf_16_le_encode' : 'interp_codecs.utf_16_le_encode',
         'utf_16_ex_decode' : 'interp_codecs.utf_16_ex_decode',
         'charbuffer_encode': 'interp_codecs.buffer_encode',
         'readbuffer_encode': 'interp_codecs.buffer_encode',
         'charmap_decode'   : 'interp_codecs.charmap_decode',
    }

    def __init__(self, space, *args):
        "NOT_RPYTHON"

        # mbcs codec is Windows specific, and based on rffi.
        if (hasattr(runicode, 'str_decode_mbcs') and
            space.config.translation.type_system != 'ootype'):
            self.interpleveldefs['mbcs_encode'] = 'interp_codecs.mbcs_encode'
            self.interpleveldefs['mbcs_decode'] = 'interp_codecs.mbcs_decode'

        MixedModule.__init__(self, space, *args)

    def setup_after_space_initialization(self):
        "NOT_RPYTHON"
        self.space.appexec([], """():
            import _codecs
            _codecs._register_existing_errors()
        """)
