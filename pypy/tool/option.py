# This is where the options for py.py are defined.
# XXX needs clean-up and reorganization.

import os
from pypy.tool import optik
make_option = optik.make_option

class Options:
    showwarning = 0
    spaces = []
    oldstyle = 0
    uselibfile = 0
    useparsermodule = "recparser" # "cpython" / "recparser" / "parser"
    compiler = "pyparse" # "cpython"
                         # "pyparse" pypy parser, cpython compiler
                         # "pycomp" pypy parser and compiler (TBD)
    version = "2.4" # "native" / "2.3" / "2.4"

def run_tb_server(option, opt, value, parser):
    from pypy.tool import tb_server
    tb_server.start()

def get_standard_options():
    options = []

    def objspace_callback(option, opt, value, parser):
        parser.values.spaces.append(value)

    options.append(make_option(
        '-o', '--objspace', action="callback", metavar='NAME',
        callback=objspace_callback,  type="string",
        help="object space to run PyPy on."))

    options.append(make_option(
        '--oldstyle', action="store_true",dest="oldstyle",
        help="enable oldstyle classes as default metaclass (std objspace only)"))
    options.append(make_option(
        '--file', action="store_true",dest="uselibfile",
        help="enable our custom file implementation"))
    options.append(make_option(
        '-w', action="store_true", dest="showwarning",
        help="enable warnings (disabled by default)"))
    options.append(make_option(
        '-H', action="callback",
        callback=run_tb_server,
        help="use web browser for traceback info"))
    options.append(make_option(
        '--compiler', action="store", type="string", dest="compiler",
        help="select the parser/compiler to use internally",
        metavar="[cpython|pyparse]"))
    options.append(make_option(
        '--parsermodule', action="store",type="string", dest="useparsermodule",
        help="select the parser module to use",
        metavar="[cpython|recparser|parser]"))
## for this to work the option module need to be loaded before the grammar!
##     options.append(make_option(
##         '--version', action="store",type="string", dest="version",
##         help="select the Python version to emulate",
##         metavar="[native|2.3|2.4]"))

    return options

def process_options(optionlist, input_options, argv=None):
    global Options
    Options = input_options
    op = optik.OptionParser()
    op.add_options(optionlist)
    options, args = op.parse_args(argv, input_options)
    return args

def objspace(name='', _spacecache={}):
    """ return singleton ObjSpace instance. 

    this is configured via the environment variable OBJSPACE
    """
    
    if not name:
        if Options.spaces:
            name = Options.spaces[-1]
        else:
            name = os.environ.get('OBJSPACE', 'std')
    
    try:
        return _spacecache[name]
    except KeyError:
        module = __import__("pypy.objspace.%s" % name, None, None, ["Space"])
        Space = module.Space
        space = Space( Options() )
        if name == 'std' and Options.oldstyle:
            space.enable_old_style_classes_as_default_metaclass()
        if Options.uselibfile:
            space.appexec([], '''():
                from _file import file
                __builtins__.file = __builtins__.open = file
            ''')
        return _spacecache.setdefault(name, space)
