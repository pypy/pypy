
"""
Mixed-module definition for the zlib module.
"""

from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    interpleveldefs = {
        'crc32': 'interp_zlib.crc32',
        'adler32': 'interp_zlib.adler32',
        'compressobj': 'interp_zlib.Compress',
        'decompressobj': 'interp_zlib.Decompress',
        }

    appleveldefs = {
        'error': 'app_zlib.error',
        'compress': 'app_zlib.compress',
        'decompress': 'app_zlib.decompress',
        }
