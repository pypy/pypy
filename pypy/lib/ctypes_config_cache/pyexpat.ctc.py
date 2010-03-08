"""
'ctypes_configure' source for pyexpat.py.
Run this to rebuild _pyexpat_cache.py.
"""

import autopath
import ctypes
from ctypes import c_char_p, c_int, c_void_p, c_char
from ctypes_configure import configure, dumpcache


class CConfigure:
    _compilation_info_ = configure.ExternalCompilationInfo(
        includes = ['expat.h'],
        libraries = ['expat'],
        pre_include_lines = [
        '#define XML_COMBINED_VERSION (10000*XML_MAJOR_VERSION+100*XML_MINOR_VERSION+XML_MICRO_VERSION)'],
        )

    XML_Char = configure.SimpleType('XML_Char', c_char)
    XML_COMBINED_VERSION = configure.ConstantInteger('XML_COMBINED_VERSION')
    for name in ['XML_PARAM_ENTITY_PARSING_NEVER',
                 'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
                 'XML_PARAM_ENTITY_PARSING_ALWAYS']:
        locals()[name] = configure.ConstantInteger(name)

    XML_Encoding = configure.Struct('XML_Encoding',[
                                    ('data', c_void_p),
                                    ('convert', c_void_p),
                                    ('release', c_void_p),
                                    ('map', c_int * 256)])
    XML_Content = configure.Struct('XML_Content',[
        ('numchildren', c_int),
        ('children', c_void_p),
        ('name', c_char_p),
        ('type', c_int),
        ('quant', c_int),
    ])
    # this is insanely stupid
    XML_FALSE = configure.ConstantInteger('XML_FALSE')
    XML_TRUE = configure.ConstantInteger('XML_TRUE')

config = configure.configure(CConfigure)

dumpcache.dumpcache(__file__, '_pyexpat_cache.py', config)
