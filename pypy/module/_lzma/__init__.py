from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    # The private part of the lzma module.

    applevel_name = '_lzma'

    interpleveldefs = {
        'LZMACompressor': 'interp_lzma.W_LZMACompressor',
        'LZMADecompressor': 'interp_lzma.W_LZMADecompressor',
        'LZMAError': 'interp_lzma.W_LZMAError',
        '_encode_filter_properties': 'interp_lzma.encode_filter_properties',
        '_decode_filter_properties': 'interp_lzma.decode_filter_properties',
    }

    for name in 'AUTO XZ ALONE RAW'.split():
        interpleveldefs['FORMAT_%s' % name] = (
            'space.wrap(interp_lzma.FORMAT_%s)' % name)
    for name in 'DEFAULT EXTREME'.split():
        interpleveldefs['PRESET_%s' % name] = (
            'space.wrap(interp_lzma.LZMA_PRESET_%s)' % name)
    for name in 'LZMA1 LZMA2 DELTA X86 IA64 ARM ARMTHUMB SPARC POWERPC'.split():
        interpleveldefs['FILTER_%s' % name] = (
            'space.wrap(interp_lzma.LZMA_FILTER_%s)' % name)

    appleveldefs = {
    }
