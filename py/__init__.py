"""
py.test and pylib: rapid testing and development utils

this module uses apipkg.py for lazy-loading sub modules
and classes.  The initpkg-dictionary  below specifies
name->value mappings where value can be another namespace
dictionary or an import path.

(c) Holger Krekel and others, 2004-2010
"""
__version__ = '1.4.3'

from py import _apipkg

# so that py.error.* instances are picklable
import sys
sys.modules['py.error'] = _apipkg.AliasModule("py.error", "py._error", 'error')

_apipkg.initpkg(__name__, attr={'_apipkg': _apipkg}, exportdefs={
    # access to all standard lib modules
    'std': '._std:std',
    # access to all posix errno's as classes
    'error': '._error:error',

    '_pydir' : '.__metainfo:pydir',
    'version': 'py:__version__', # backward compatibility

    # pytest-2.0 has a flat namespace, we use alias modules
    # to keep old references compatible
    'test' : 'pytest',
    'test.collect' : 'pytest',
    'test.cmdline' : 'pytest',

    # hook into the top-level standard library
    'process' : {
        '__doc__'        : '._process:__doc__',
        'cmdexec'        : '._process.cmdexec:cmdexec',
        'kill'           : '._process.killproc:kill',
        'ForkedFunc'     : '._process.forkedfunc:ForkedFunc',
    },

    'apipkg' : {
        'initpkg'   : '._apipkg:initpkg',
        'ApiModule' : '._apipkg:ApiModule',
    },

    'iniconfig' : {
        'IniConfig'      : '._iniconfig:IniConfig',
        'ParseError'     : '._iniconfig:ParseError',
    },

    'path' : {
        '__doc__'        : '._path:__doc__',
        'svnwc'          : '._path.svnwc:SvnWCCommandPath',
        'svnurl'         : '._path.svnurl:SvnCommandPath',
        'local'          : '._path.local:LocalPath',
        'SvnAuth'        : '._path.svnwc:SvnAuth',
    },

    # python inspection/code-generation API
    'code' : {
        '__doc__'           : '._code:__doc__',
        'compile'           : '._code.source:compile_',
        'Source'            : '._code.source:Source',
        'Code'              : '._code.code:Code',
        'Frame'             : '._code.code:Frame',
        'ExceptionInfo'     : '._code.code:ExceptionInfo',
        'Traceback'         : '._code.code:Traceback',
        'getfslineno'       : '._code.source:getfslineno',
        'getrawcode'        : '._code.code:getrawcode',
        'patch_builtins'    : '._code.code:patch_builtins',
        'unpatch_builtins'  : '._code.code:unpatch_builtins',
        '_AssertionError'   : '._code.assertion:AssertionError',
        '_reinterpret_old'  : '._code.assertion:reinterpret_old',
        '_reinterpret'      : '._code.assertion:reinterpret',
        '_reprcompare'      : '._code.assertion:_reprcompare',
    },

    # backports and additions of builtins
    'builtin' : {
        '__doc__'        : '._builtin:__doc__',
        'enumerate'      : '._builtin:enumerate',
        'reversed'       : '._builtin:reversed',
        'sorted'         : '._builtin:sorted',
        'any'            : '._builtin:any',
        'all'            : '._builtin:all',
        'set'            : '._builtin:set',
        'frozenset'      : '._builtin:frozenset',
        'BaseException'  : '._builtin:BaseException',
        'GeneratorExit'  : '._builtin:GeneratorExit',
        '_sysex'         : '._builtin:_sysex',
        'print_'         : '._builtin:print_',
        '_reraise'       : '._builtin:_reraise',
        '_tryimport'     : '._builtin:_tryimport',
        'exec_'          : '._builtin:exec_',
        '_basestring'    : '._builtin:_basestring',
        '_totext'        : '._builtin:_totext',
        '_isbytes'       : '._builtin:_isbytes',
        '_istext'        : '._builtin:_istext',
        '_getimself'     : '._builtin:_getimself',
        '_getfuncdict'   : '._builtin:_getfuncdict',
        '_getcode'       : '._builtin:_getcode',
        'builtins'       : '._builtin:builtins',
        'execfile'       : '._builtin:execfile',
        'callable'       : '._builtin:callable',
    },

    # input-output helping
    'io' : {
        '__doc__'             : '._io:__doc__',
        'dupfile'             : '._io.capture:dupfile',
        'TextIO'              : '._io.capture:TextIO',
        'BytesIO'             : '._io.capture:BytesIO',
        'FDCapture'           : '._io.capture:FDCapture',
        'StdCapture'          : '._io.capture:StdCapture',
        'StdCaptureFD'        : '._io.capture:StdCaptureFD',
        'TerminalWriter'      : '._io.terminalwriter:TerminalWriter',
        'ansi_print'          : '._io.terminalwriter:ansi_print',
        'get_terminal_width'  : '._io.terminalwriter:get_terminal_width',
        'saferepr'            : '._io.saferepr:saferepr',
    },

    # small and mean xml/html generation
    'xml' : {
        '__doc__'            : '._xmlgen:__doc__',
        'html'               : '._xmlgen:html',
        'Tag'                : '._xmlgen:Tag',
        'raw'                : '._xmlgen:raw',
        'Namespace'          : '._xmlgen:Namespace',
        'escape'             : '._xmlgen:escape',
    },

    'log' : {
        # logging API ('producers' and 'consumers' connected via keywords)
        '__doc__'            : '._log:__doc__',
        '_apiwarn'           : '._log.warning:_apiwarn',
        'Producer'           : '._log.log:Producer',
        'setconsumer'        : '._log.log:setconsumer',
        '_setstate'          : '._log.log:setstate',
        '_getstate'          : '._log.log:getstate',
        'Path'               : '._log.log:Path',
        'STDOUT'             : '._log.log:STDOUT',
        'STDERR'             : '._log.log:STDERR',
        'Syslog'             : '._log.log:Syslog',
    },

})
