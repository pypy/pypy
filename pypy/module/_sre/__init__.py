from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """A pure Python reimplementation of the _sre module from CPython 2.4
Copyright 2005 Nik Haldimann, licensed under the MIT license

This code is based on material licensed under CNRI's Python 1.6 license and
copyrighted by: Copyright (c) 1997-2001 by Secret Labs AB
"""
    
    appleveldefs = {
        'CODESIZE':       'app_info.CODESIZE',
        'MAGIC':          'app_info.MAGIC',
        'copyright':      'app_info.copyright',
        'getcodesize':    'app_info.getcodesize',
        'compile':        'app_sre.compile',
        'getlower':       'app_sre.getlower',
    }

    interpleveldefs = {
        '_is_digit':      'interp_sre._is_digit',
        '_is_space':      'interp_sre._is_space',
        '_is_word':       'interp_sre._is_word',
        '_is_linebreak':  'interp_sre._is_linebreak',
    }
