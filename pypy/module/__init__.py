
# ObjSpaces that implement the standard Python semantics
_std_spaces = ['TrivialObjSpace','StdObjSpace']

_all_spaces = _std_spaces + ['FlowObjSpace']

# The following item ia a list of
#   (filename, classname, [applicable spaces]) tuples describing the
#   builtin modules (pypy.interpreter.extmodule.ExtModule)
#   availible in the pypy.module directory. 

# classname should be a classname of a callable in 'filename' that returns
#   an unwrapped builtin module instance (pypy.interpreter.extmodule.ExtModule
#   instance) - it may return an unwrapped None if the builtin module is not
#   to be loaded. (e.g. this is the wrong platform.)

#Note: the builtin and sys modules are special cased for bootstrapping reasons.

# But this is an example of what the list would look like:

##_builtin_and_sys = [('builtin','__builtin__',_std_spaces),
##                    ('sysmodule','Sys',_std_spaces),
##                    ]

_builtin_modules = [('os_modules','Posix',_std_spaces),
                    ('os_modules','Nt',_std_spaces),
                    ('os_modules','Os2',_std_spaces),
                    ('os_modules','Mac',_std_spaces),
                    ('os_modules','Ce',_std_spaces),
                    ('os_modules','Riscos',_std_spaces),
                    ('mathmodule','Math',_std_spaces),
                    ('_randommodule','RandomHelper',_std_spaces),
                    ('cStringIOmodule','CStringIO',_std_spaces),
                    ('itertoolsmodule','Itertools',_std_spaces),
                    ('_sremodule','SreHelper',_std_spaces),
                    ]
