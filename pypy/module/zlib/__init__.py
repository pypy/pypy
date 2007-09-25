
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
        'compress': 'interp_zlib.compress',
        'decompress': 'interp_zlib.decompress',
        }

    appleveldefs = {
        'error': 'app_zlib.error',
        }
