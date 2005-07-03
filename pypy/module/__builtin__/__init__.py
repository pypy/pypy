from pypy.interpreter.error import OperationError
from pypy.interpreter import module
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Built-in functions, exceptions, and other objects."""

    appleveldefs = {
        'quit'          : 'app_help.exit',
        'exit'          : 'app_help.exit',
        'copyright'     : 'app_help.copyright',
        'license'       : 'app_help.license',
        'help'          : 'app_help.help',

        'execfile'      : 'app_io.execfile',
        'raw_input'     : 'app_io.raw_input',
        'input'         : 'app_io.input',

        'sum'           : 'app_functional.sum',
        'apply'         : 'app_functional.apply',
        'map'           : 'app_functional.map',
        'filter'        : 'app_functional.filter',
        'zip'           : 'app_functional.zip',
        'reduce'        : 'app_functional.reduce',
        'range'         : 'app_functional.range',
        'min'           : 'app_functional.min',
        'max'           : 'app_functional.max',
        'enumerate'     : 'app_functional.enumerate',
        'xrange'        : 'app_functional.xrange',
        'sorted'        : 'app_functional.sorted',
        'reversed'      : 'app_functional.reversed',

        'issubclass'    : 'app_inspect.issubclass',
        'isinstance'    : 'app_inspect.isinstance',
        'hasattr'       : 'app_inspect.hasattr',
        'callable'      : 'app_inspect.callable',
        'globals'       : 'app_inspect.globals',
        'locals'        : 'app_inspect.locals',
        'vars'          : 'app_inspect.vars',
        'dir'           : 'app_inspect.dir',

        'property'      : 'app_descriptor.property',
        'staticmethod'  : 'app_descriptor.staticmethod',
        'classmethod'   : 'app_descriptor.classmethod',
        'super'         : 'app_descriptor.super',

        'complex'       : 'app_complex.complex',

        'intern'        : 'app_misc.intern',
        'buffer'        : 'app_buffer.buffer',
        'reload'        : 'app_misc.reload',

        'set'           : 'app_sets.set',
        'frozenset'     : 'app_sets.frozenset',
    }

    interpleveldefs = {
        # constants
        '__name__'      : '(space.wrap("__builtin__"))', 
        '__doc__'       : '(space.wrap("PyPy builtin module"))', 
        'None'          : '(space.w_None)',
        'False'         : '(space.w_False)',
        'True'          : '(space.w_True)',
        '__debug__'     : '(space.w_True)',      # XXX
        'type'          : '(space.w_type)',
        'object'        : '(space.w_object)',
        'file'          : '(space.wrap(file))',
        'open'          : '(space.wrap(file))',
        'unicode'       : '(space.w_unicode)',

        # old-style classes dummy support
        '_classobj'     : 'space.w_classobj',
        '_instance'     : 'space.w_instance',
        # default __metaclass__
        # XXX can use _classobj when we have a working one integrated
        '__metaclass__' : '(space.w_type)',

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
        'getattr'       : 'operation.getattr',
        'setattr'       : 'operation.setattr',
        'delattr'       : 'operation.delattr',
        'iter'          : 'operation.iter',
        'hash'          : 'operation.hash',
        'id'            : 'operation.id',
        '_seqiter'      : 'operation._seqiter',

        'compile'       : 'compiling.compile',
        'eval'          : 'compiling.eval',

        '__import__'    : 'importing.importhook',
    }

    def pick_builtin(self, w_globals):
       "Look up the builtin module to use from the __builtins__ global"
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
