from pypy.interpreter.lazymodule import LazyModule 
from pypy.interpreter.error import OperationError 

class Module(LazyModule):
    """Sys Builtin Module. """
    def __init__(self, space, w_name):
        """NOT_RPYTHON""" # because parent __init__ isn't
        super(Module, self).__init__(space, w_name) 
        self.checkinterval = 100
        self.recursionlimit = 100
        
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
        'stdin'                 : 'space.wrap(sys.stdin)',
        '__stdin__'             : 'space.wrap(sys.stdin)',
        'stdout'                : 'space.wrap(sys.stdout)',
        '__stdout__'            : 'space.wrap(sys.stdout)',
        'stderr'                : 'space.wrap(sys.stderr)', 
        '__stderr__'            : 'space.wrap(sys.stderr)',
        'pypy_objspaceclass'    : 'space.wrap(repr(space))',

        'path'                  : 'state.get(space).w_path', 
        'modules'               : 'state.get(space).w_modules', 
        'argv'                  : 'state.get(space).w_argv', 
        'warnoptions'           : 'state.get(space).w_warnoptions', 
        'builtin_module_names'  : 'state.get(space).w_builtin_module_names', 
        'pypy_getudir'          : 'state.pypy_getudir', 

        'getdefaultencoding'    : 'state.getdefaultencoding', 
        'getrefcount'           : 'vm.getrefcount', 
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
        'copyright'             : 'space.wrap("MIT-License")', 
        'api_version'           : 'space.wrap(1012)', 
        'version_info'          : 'space.wrap((2,3,4, "alpha", 42))', 
        'version'               : 'space.wrap("2.3.4 (pypy1 build)")', 
        'hexversion'            : 'space.wrap(0x020304a0)', 
        'ps1'                   : 'space.wrap(">>>>")', 
        'ps2'                   : 'space.wrap("....")', 

        'displayhook'           : 'hook.displayhook', 
        '__displayhook__'       : 'hook.__displayhook__', 
    }
    appleveldefs = {
        #'displayhook'           : 'app.displayhook', 
        #'__displayhook__'       : 'app.__displayhook__', 
        'excepthook'            : 'app.excepthook', 
        '__excepthook__'        : 'app.excepthook', 
        'exit'                  : 'app.exit', 
        'getfilesystemencoding' : 'app.getfilesystemencoding', 
        'callstats'             : 'app.callstats',
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

    def getdictvalue(self, space, attr): 
        """ specialize access to dynamic exc_* attributes. """ 
        value = LazyModule.getdictvalue(self, space, attr) 
        if value is not None: 
            return value 
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
