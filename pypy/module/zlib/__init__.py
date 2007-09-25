
"""
Mixed-module definition for the zlib module.
"""

from pypy.interpreter.mixedmodule import MixedModule
from pypy.rlib import rzlib


class Module(MixedModule):
    interpleveldefs = {
        'crc32': 'interp_zlib.crc32',
        'adler32': 'interp_zlib.adler32',
        'compressobj': 'interp_zlib.Compress',
        'decompressobj': 'interp_zlib.Decompress',
        'compress': 'interp_zlib.compress',
        'decompress': 'interp_zlib.decompress',
        '__version__': 'space.wrap("1.0")',
        }

    appleveldefs = {
        'error': 'app_zlib.error',
        }


for _name in """
    MAX_WBITS  DEFLATED  DEF_MEM_LEVEL
    Z_BEST_SPEED  Z_BEST_COMPRESSION  Z_DEFAULT_COMPRESSION
    Z_FILTERED  Z_HUFFMAN_ONLY  Z_DEFAULT_STRATEGY
    Z_FINISH  Z_NO_FLUSH  Z_SYNC_FLUSH  Z_FULL_FLUSH
    ZLIB_VERSION
    """.split():
    Module.interpleveldefs[_name] = 'space.wrap(%r)' % (getattr(rzlib, _name),)
