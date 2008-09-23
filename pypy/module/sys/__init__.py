from pypy.interpreter.mixedmodule import MixedModule 
from pypy.interpreter.error import OperationError 

class Module(MixedModule):
    """Sys Builtin Module. """
    def __init__(self, space, w_name):
        """NOT_RPYTHON""" # because parent __init__ isn't
        super(Module, self).__init__(space, w_name) 
        self.checkinterval = 100
        self.recursionlimit = 100
        self.w_default_encoder = None
        self.defaultencoding = "ascii"
        
    interpleveldefs = {
        '__name__'              : '(space.wrap("sys"))', 
        '__doc__'               : '(space.wrap("PyPy sys module"))', 

        'platform'              : 'space.wrap(sys.platform)', 
        'maxint'                : 'space.wrap(sys.maxint)', 
        'byteorder'             : 'space.wrap(sys.byteorder)', 
        'exec_prefix'           : 'space.wrap(sys.exec_prefix)', 
        'prefix'                : 'space.wrap(sys.prefix)', 
        'maxunicode'            : 'space.wrap(sys.maxunicode)',
        'maxint'                : 'space.wrap(sys.maxint)',
        'stdin'                 : 'state.getio(space).w_stdin',
        '__stdin__'             : 'state.getio(space).w_stdin',
        'stdout'                : 'state.getio(space).w_stdout',
        '__stdout__'            : 'state.getio(space).w_stdout',
        'stderr'                : 'state.getio(space).w_stderr',
        '__stderr__'            : 'state.getio(space).w_stderr',
        'pypy_objspaceclass'    : 'space.wrap(repr(space))',

        'path'                  : 'state.get(space).w_path', 
        'modules'               : 'state.get(space).w_modules', 
        'argv'                  : 'state.get(space).w_argv', 
        'warnoptions'           : 'state.get(space).w_warnoptions', 
        'builtin_module_names'  : 'state.w_None',
        'pypy_getudir'          : 'state.pypy_getudir', 
        'pypy_initial_path'     : 'state.pypy_initial_path',

        '_getframe'             : 'vm._getframe', 
        'setrecursionlimit'     : 'vm.setrecursionlimit', 
        'getrecursionlimit'     : 'vm.getrecursionlimit', 
        'setcheckinterval'      : 'vm.setcheckinterval', 
        'getcheckinterval'      : 'vm.getcheckinterval', 
        'exc_info'              : 'vm.exc_info', 
        'exc_clear'             : 'vm.exc_clear', 
        'settrace'              : 'vm.settrace',
        'setprofile'            : 'vm.setprofile',
        'call_tracing'          : 'vm.call_tracing',
        
        'executable'            : 'space.wrap("py.py")', 
        'api_version'           : 'version.get_api_version(space)',
        'version_info'          : 'version.get_version_info(space)',
        'version'               : 'version.get_version(space)',
        'pypy_version_info'     : 'version.get_pypy_version_info(space)',
        'pypy_svn_url'          : 'version.get_svn_url(space)',
        'hexversion'            : 'version.get_hexversion(space)',
        'ps1'                   : 'space.wrap(">>>> ")', 
        'ps2'                   : 'space.wrap(".... ")', 

        'displayhook'           : 'hook.displayhook', 
        '__displayhook__'       : 'hook.__displayhook__', 
        'meta_path'             : 'space.wrap([])',
        'path_hooks'            : 'space.wrap([])',
        'path_importer_cache'   : 'space.wrap({})',
        #'subversion'           : added in Python 2.5
        
        'getdefaultencoding'    : 'interp_encoding.getdefaultencoding', 
        'setdefaultencoding'    : 'interp_encoding.setdefaultencoding',
        # XXX hack
        '_magic'                : 'version._magic',
}
    appleveldefs = {
        #'displayhook'           : 'app.displayhook', 
        #'__displayhook__'       : 'app.__displayhook__', 
        'excepthook'            : 'app.excepthook', 
        '__excepthook__'        : 'app.excepthook', 
        'exit'                  : 'app.exit', 
        'exitfunc'              : 'app.exitfunc',
        'getfilesystemencoding' : 'app.getfilesystemencoding', 
        'callstats'             : 'app.callstats',
        'copyright'             : 'app.copyright_str', 
    }

    def setbuiltinmodule(self, w_module, name): 
        w_name = self.space.wrap(name)
        w_modules = self.get('modules')
        self.space.setitem(w_modules, w_name, w_module)

    def getmodule(self, name): 
        space = self.space
        w_modules = self.get('modules') 
        try: 
            return space.getitem(w_modules, space.wrap(name))
        except OperationError, e: 
            if not e.match(space, space.w_KeyError): 
                raise 
            return None 

    def setmodule(self, w_module): 
        space = self.space
        w_name = self.space.getattr(w_module, space.wrap('__name__'))
        w_modules = self.get('modules')
        self.space.setitem(w_modules, w_name, w_module)

    def getdictvalue(self, space, w_attr): 
        """ specialize access to dynamic exc_* attributes. """ 
        value = MixedModule.getdictvalue(self, space, w_attr) 
        if value is not None: 
            return value
        attr = space.str_w(w_attr)
        if attr == 'exc_type':
            operror = space.getexecutioncontext().sys_exc_info()
            if operror is None:
                return space.w_None
            else:
                return operror.w_type
        elif attr == 'exc_value':
            operror = space.getexecutioncontext().sys_exc_info()
            if operror is None:
                return space.w_None
            else:
                return operror.w_value
        elif attr == 'exc_traceback':
            operror = space.getexecutioncontext().sys_exc_info()
            if operror is None:
                return space.w_None
            else:
                return space.wrap(operror.application_traceback)
        return None 

    def get_w_default_encoder(self):
        if self.w_default_encoder is not None:
            # XXX is this level of caching ok?  CPython has some shortcuts
            # for common encodings, but as far as I can see it has no general
            # cache.
            return self.w_default_encoder
        else:
            from pypy.module.sys.interp_encoding import get_w_default_encoder
            return get_w_default_encoder(self.space)
