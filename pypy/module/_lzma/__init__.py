from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    # The private part of the lzma module.

    applevel_name = '_lzma'

    interpleveldefs = {
        'LZMACompressor': 'interp_lzma.W_LZMACompressor',
        'LZMADecompressor': 'interp_lzma.W_LZMADecompressor',
        '_encode_filter_properties': 'interp_lzma.encode_filter_properties',
        '_decode_filter_properties': 'interp_lzma.decode_filter_properties',
        'FORMAT_AUTO': 'space.wrap(interp_lzma.FORMAT_AUTO)',
        'FORMAT_XZ': 'space.wrap(interp_lzma.FORMAT_XZ)',
        'FORMAT_ALONE': 'space.wrap(interp_lzma.FORMAT_ALONE)',
        'FORMAT_RAW': 'space.wrap(interp_lzma.FORMAT_RAW)',
    }

    appleveldefs = {
    }
