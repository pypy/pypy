from pypy.interpreter.error import OperationError
from pypy.interpreter import module
from pypy.interpreter.mixedmodule import MixedModule

# put builtins here that should be optimized somehow

OPTIMIZED_BUILTINS = ["len", "range", "xrange", "min", "max", "enumerate",
        "isinstance", "type", "zip", "file", "open", "abs", "chr", "unichr",
        "ord", "pow", "repr", "hash", "oct", "hex", "round", "cmp", "getattr",
        "setattr", "delattr", "callable", "int", "str", "float"]

assert len(OPTIMIZED_BUILTINS) <= 256

BUILTIN_TO_INDEX = {}

for i, name in enumerate(OPTIMIZED_BUILTINS):
    BUILTIN_TO_INDEX[name] = i

assert len(OPTIMIZED_BUILTINS) == len(BUILTIN_TO_INDEX)

class Module(MixedModule):
    """Built-in functions, exceptions, and other objects."""
    expose__file__attribute = False

    appleveldefs = {
        'execfile'      : 'app_io.execfile',
        'raw_input'     : 'app_io.raw_input',
        'input'         : 'app_io.input',

        'sum'           : 'app_functional.sum',
        'apply'         : 'app_functional.apply',
        'map'           : 'app_functional.map',
        'filter'        : 'app_functional.filter',
        'zip'           : 'app_functional.zip',
        'reduce'        : 'app_functional.reduce',
        #'range'         : 'app_functional.range',
        # redirected to functional.py, applevel version
        # is still needed and should stay where it is.
        'min'           : 'app_functional.min',
        'max'           : 'app_functional.max',
        'enumerate'     : 'app_functional.enumerate',
        'sorted'        : 'app_functional.sorted',
        'reversed'      : 'app_functional.reversed',
        '_install_pickle_support_for_reversed_iterator':
        'app_functional._install_pickle_support_for_reversed_iterator',

        'globals'       : 'app_inspect.globals',
        'locals'        : 'app_inspect.locals',
        'vars'          : 'app_inspect.vars',
        'dir'           : 'app_inspect.dir',

        'reload'        : 'app_misc.reload',

        '__filestub'    : 'app_file_stub.file',
    }

    interpleveldefs = {
        # constants
        'None'          : '(space.w_None)',
        'False'         : '(space.w_False)',
        'True'          : '(space.w_True)',
        '__debug__'     : '(space.w_True)',      # XXX
        'type'          : '(space.w_type)',
        'object'        : '(space.w_object)',
        'unicode'       : '(space.w_unicode)',
        'buffer'        : 'operation.Buffer',

        'file'          : 'state.get(space).w_file',
        'open'          : 'state.get(space).w_file',

        # default __metaclass__: old-style class
        '__metaclass__' : 'interp_classobj.W_ClassObject',

        # interp-level function definitions
        'abs'           : 'operation.abs',
        'chr'           : 'operation.chr',
        'unichr'        : 'operation.unichr',
        'len'           : 'operation.len',
        'ord'           : 'operation.ord',
        'pow'           : 'operation.pow',
        'repr'          : 'operation.repr',
        'hash'          : 'operation.hash',
        'oct'           : 'operation.oct',
        'hex'           : 'operation.hex',
        'round'         : 'operation.round',
        'cmp'           : 'operation.cmp',
        'coerce'        : 'operation.coerce',
        'divmod'        : 'operation.divmod',
        '_issubtype'    : 'operation._issubtype',
        'issubclass'    : 'abstractinst.app_issubclass',
        'isinstance'    : 'abstractinst.app_isinstance',
        'getattr'       : 'operation.getattr',
        'setattr'       : 'operation.setattr',
        'delattr'       : 'operation.delattr',
        'hasattr'       : 'operation.hasattr',
        'iter'          : 'operation.iter',
        'id'            : 'operation.id',
        'intern'        : 'operation.intern',
        'callable'      : 'operation.callable',

        'compile'       : 'compiling.compile',
        'eval'          : 'compiling.eval',

        '__import__'    : 'importing.importhook',

        'range'         : 'functional.range_int',
        'xrange'        : 'functional.W_XRange',
        'all'           : 'functional.all',
        'any'           : 'functional.any',
        'super'         : 'descriptor.W_Super',
        'staticmethod'  : 'descriptor.StaticMethod',
        'classmethod'   : 'descriptor.ClassMethod',
        'property'      : 'descriptor.W_Property',

    }

    def pick_builtin(self, w_globals):
       "Look up the builtin module to use from the __builtins__ global"
       # pick the __builtins__ roughly in the same way CPython does it
       # this is obscure and slow
       space = self.space
       try:
           w_builtin = space.getitem(w_globals, space.wrap('__builtins__'))
       except OperationError, e:
           if not e.match(space, space.w_KeyError):
               raise
       else:
           if w_builtin is space.builtin:   # common case
               return space.builtin
           if space.is_true(space.isinstance(w_builtin, space.w_dict)):
                return module.Module(space, None, w_builtin)
           builtin = space.interpclass_w(w_builtin)
           if isinstance(builtin, module.Module):
               return builtin   
       # no builtin! make a default one.  Given them None, at least.
       builtin = module.Module(space, None)
       space.setitem(builtin.w_dict, space.wrap('None'), space.w_None)
       return builtin

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        space = self.space
        self.builtins_by_index = [None] * len(OPTIMIZED_BUILTINS)
        for i, name in enumerate(OPTIMIZED_BUILTINS):
            self.builtins_by_index[i] = space.getattr(self, space.wrap(name))
        # call installations for pickle support
        for name in self.loaders.keys():
            if name.startswith('_install_pickle_support_for_'):
                w_install = self.get(name)
                space.call_function(w_install)
                # xxx hide the installer
                space.delitem(self.w_dict, space.wrap(name))
                del self.loaders[name]
        # install the more general version of isinstance() & co. in the space
        from pypy.module.__builtin__ import abstractinst as ab
        space.abstract_isinstance_w = ab.abstract_isinstance_w.__get__(space)
        space.abstract_issubclass_w = ab.abstract_issubclass_w.__get__(space)
        space.abstract_isclass_w = ab.abstract_isclass_w.__get__(space)
        space.abstract_getclass = ab.abstract_getclass.__get__(space)

    def startup(self, space):
        # install zipimport hook if --withmod-zipimport is used
        if space.config.objspace.usemodules.zipimport:
            w_import = space.builtin.get('__import__')
            w_zipimport = space.call(w_import, space.newlist(
                [space.wrap('zipimport')]))
            w_sys = space.getbuiltinmodule('sys')
            w_path_hooks = space.getattr(w_sys, space.wrap('path_hooks'))
            w_append = space.getattr(w_path_hooks, space.wrap('append'))
            w_zipimporter = space.getattr(w_zipimport,
                                          space.wrap('zipimporter'))
            space.call(w_append, space.newlist([w_zipimporter]))
