"""
   _sre_pypy

   A pypy interpreter-level implementation of the _sre module which is
   implemented by invoking _sre from the underlying interpreter and
   wrapping the results.
   
   We hope someday to replace the C dependency; hopefully this module
   allows us to do so one piece at a time.
"""

from pypy.interpreter.lazymodule import LazyModule 


class Module(LazyModule):
    """_sre_pypy module"""
    
    appleveldefs = {
        '__name__':       'application_code.__name__',
        '__doc__':        'application_code.__doc__',
        'getcodesize':    'application_code.getcodesize',
        'compile':        'application_code.compile',
        'SRE_Pattern':    'application_code.SRE_Pattern',
        'SRE_Match':      'application_code.SRE_Match',
    }

    interpleveldefs = {
        # constants
        'MAGIC'         : '(space.wrap(interpreter_code._sre.MAGIC))',
        'CODESIZE'      : '(space.wrap(interpreter_code._sre.CODESIZE))',
        'getlower'               : 'interpreter_code.getlower',
        '_compile'               : 'interpreter_code._compile',
        '_fget'                  : 'interpreter_code._fget',
        '_SRE_Pattern_match'     : 'interpreter_code._SRE_Pattern_match',
        '_SRE_Pattern_search'    : 'interpreter_code._SRE_Pattern_search',
        '_SRE_Pattern_findall'   : 'interpreter_code._SRE_Pattern_findall',
        '_SRE_Pattern_sub'       : 'interpreter_code._SRE_Pattern_sub',
        '_SRE_Pattern_subn'      : 'interpreter_code._SRE_Pattern_subn',
        '_SRE_Pattern_split'     : 'interpreter_code._SRE_Pattern_split',
        '_SRE_Pattern_finditer'  : 'interpreter_code._SRE_Pattern_finditer',
        '_SRE_Pattern_scanner'   : 'interpreter_code._SRE_Pattern_scanner',
        '_SRE_Match_start'       : 'interpreter_code._SRE_Match_start',
        '_SRE_Match_end'         : 'interpreter_code._SRE_Match_end',
        '_SRE_Match_expand'      : 'interpreter_code._SRE_Match_expand',
        '_SRE_Match_span'        : 'interpreter_code._SRE_Match_span',
        '_SRE_Match_groups'      : 'interpreter_code._SRE_Match_groups',
        '_SRE_Match_groupdict'   : 'interpreter_code._SRE_Match_groupdict',
        '_SRE_Match_group'       : 'interpreter_code._SRE_Match_group',
        '_SRE_Finditer_next'     : 'interpreter_code._SRE_Finditer_next',
        '_SRE_Scanner_match'     : 'interpreter_code._SRE_Scanner_match',
        '_SRE_Scanner_search'    : 'interpreter_code._SRE_Scanner_search',
    }

