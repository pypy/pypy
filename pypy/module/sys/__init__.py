from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib import rdynload
import sys

_WIN = sys.platform == 'win32'

class Module(MixedModule):
    """Sys Builtin Module. """
    _immutable_fields_ = ["defaultencoding", "debug?"]

    def __init__(self, space, w_name):
        """NOT_RPYTHON""" # because parent __init__ isn't
        if space.config.translating:
            del self.__class__.interpleveldefs['pypy_getudir']
        super(Module, self).__init__(space, w_name)
        self.recursionlimit = 100
        self.defaultencoding = "utf-8"
        self.filesystemencoding = None
        self.debug = True
        self.track_resources = False
        self.dlopenflags = rdynload._dlopen_default_mode()

    interpleveldefs = {
        '__name__'              : '(space.wrap("sys"))',
        '__doc__'               : '(space.wrap("PyPy sys module"))',

        'platform'              : 'space.wrap(system.PLATFORM)',
        'maxsize'               : 'space.wrap(sys.maxint)',
        'byteorder'             : 'space.wrap(sys.byteorder)',
        'maxunicode'            : 'space.wrap(vm.MAXUNICODE)',
        'pypy_objspaceclass'    : 'space.wrap(repr(space))',
        #'prefix'               : # added by pypy_initial_path() when it
        #'exec_prefix'          : # succeeds, pointing to trunk or /usr
        'path'                  : 'state.get(space).w_path',
        'modules'               : 'state.get(space).w_modules',
        'argv'                  : 'state.get(space).w_argv',
        'warnoptions'           : 'state.get(space).w_warnoptions',
        'abiflags'              : 'space.wrap("")',
        'builtin_module_names'  : 'space.w_None',
        'pypy_getudir'          : 'state.pypy_getudir',    # not translated
        'pypy_find_stdlib'      : 'initpath.pypy_find_stdlib',
        'pypy_find_executable'  : 'initpath.pypy_find_executable',
        'pypy_resolvedirof'     : 'initpath.pypy_resolvedirof',
        'pypy_initfsencoding'   : 'initpath.pypy_initfsencoding',

        '_getframe'             : 'vm._getframe',
        '_current_frames'       : 'currentframes._current_frames',
        'setrecursionlimit'     : 'vm.setrecursionlimit',
        'getrecursionlimit'     : 'vm.getrecursionlimit',
        'setcheckinterval'      : 'vm.setcheckinterval',
        'getcheckinterval'      : 'vm.getcheckinterval',
        'exc_info'              : 'vm.exc_info',
        'settrace'              : 'vm.settrace',
        'gettrace'              : 'vm.gettrace',
        'setprofile'            : 'vm.setprofile',
        'getprofile'            : 'vm.getprofile',
        'call_tracing'          : 'vm.call_tracing',
        'getsizeof'             : 'vm.getsizeof',
        'intern'                : 'vm.intern',

        'api_version'           : 'version.get_api_version(space)',
        'version_info'          : 'version.get_version_info(space)',
        #'version'              : set in startup()
        'pypy_version_info'     : 'version.get_pypy_version_info(space)',
        'subversion'            : 'version.get_subversion_info(space)',
        '_mercurial'            : 'version.get_repo_info(space)',
        'hexversion'            : 'version.get_hexversion(space)',

        'displayhook'           : 'hook.displayhook',
        '__displayhook__'       : 'hook.__displayhook__',
        'meta_path'             : 'space.wrap([])',
        'path_hooks'            : 'space.wrap([])',
        'path_importer_cache'   : 'space.wrap({})',
        'dont_write_bytecode'   : 'space.wrap(space.config.translation.sandbox)',

        'getdefaultencoding'    : 'interp_encoding.getdefaultencoding',
        'getfilesystemencoding' : 'interp_encoding.getfilesystemencoding',

        'float_info'            : 'system.get_float_info(space)',
        'int_info'              : 'system.get_int_info(space)',
        'hash_info'             : 'system.get_hash_info(space)',
        'float_repr_style'      : 'system.get_float_repr_style(space)',
        'getdlopenflags'        : 'system.getdlopenflags',
        'setdlopenflags'        : 'system.setdlopenflags',
        }

    if sys.platform == 'win32':
        interpleveldefs['winver'] = 'version.get_winver(space)'
        interpleveldefs['getwindowsversion'] = 'vm.getwindowsversion'

    appleveldefs = {
        'excepthook'            : 'app.excepthook',
        '__excepthook__'        : 'app.excepthook',
        'exit'                  : 'app.exit',
        'callstats'             : 'app.callstats',
        'copyright'             : 'app.copyright_str',
        'flags'                 : 'app.null_sysflags',
        '_xoptions'             : 'app.null__xoptions',
        'implementation'        : 'app.implementation',
    }

    def startup(self, space):
        if space.config.translating:
            assert self.filesystemencoding is None

        if not space.config.translating or we_are_translated():
            from pypy.module.sys import version
            space.setitem(self.w_dict, space.wrap("version"),
                          space.wrap(version.get_version(space)))
            if _WIN:
                from pypy.module.sys import vm
                w_handle = vm.get_dllhandle(space)
                space.setitem(self.w_dict, space.wrap("dllhandle"), w_handle)

        from pypy.module.sys import system
        thread_info = system.get_thread_info(space)
        if thread_info is not None:
            space.setitem(self.w_dict, space.wrap('thread_info'), thread_info)

    def setup_after_space_initialization(self):
        space = self.space

        if not space.config.translating:
            from pypy.module.sys.interp_encoding import _getfilesystemencoding
            self.filesystemencoding = _getfilesystemencoding(space)

        if not space.config.translating:
            # Install standard streams for tests that don't call app_main.
            # Always use line buffering, even for tests that capture
            # standard descriptors.
            space.appexec([], """():
                import sys, io
                sys.stdin = sys.__stdin__ = io.open(0, "r", encoding="ascii",
                                                    closefd=False)
                sys.stdin.buffer.raw.name = "<stdin>"
                sys.stdout = sys.__stdout__ = io.open(1, "w", encoding="ascii",
                                                      buffering=1,
                                                      closefd=False)
                sys.stdout.buffer.raw.name = "<stdout>"
                sys.stderr = sys.__stderr__ = io.open(2, "w", encoding="ascii",
                                                      errors="backslashreplace",
                                                      buffering=1,
                                                      closefd=False)
                sys.stderr.buffer.raw.name = "<stderr>"
               """)

    def flush_std_files(self, space):
        w_stdout = space.sys.getdictvalue(space, 'stdout')
        w_stderr = space.sys.getdictvalue(space, 'stderr')
        for w_file in [w_stdout, w_stderr]:
            if not (space.is_none(w_file) or
                    self._file_is_closed(space, w_file)):
                try:
                    space.call_method(w_file, 'flush')
                except OperationError as e:
                    if w_file is w_stdout:
                        e.write_unraisable(space, '', w_file)

    def _file_is_closed(self, space, w_file):
        try:
            w_closed = space.getattr(w_file, space.wrap('closed'))
        except OperationError:
            return False
        return space.bool_w(w_closed)

    def getmodule(self, name):
        space = self.space
        w_modules = self.get('modules')
        try:
            return space.getitem(w_modules, space.wrap(name))
        except OperationError as e:
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
        value = MixedModule.getdictvalue(self, space, attr)
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
                return operror.get_w_value(space)
        elif attr == 'exc_traceback':
            operror = space.getexecutioncontext().sys_exc_info()
            if operror is None:
                return space.w_None
            else:
                return space.wrap(operror.get_traceback())
        return None

    def get_flag(self, name):
        space = self.space
        return space.int_w(space.getattr(self.get('flags'), space.wrap(name)))

    def get_state(self, space):
        from pypy.module.sys import state
        return state.get(space)
