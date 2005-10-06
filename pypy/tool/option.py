# This is where the options for py.py are defined.
# XXX needs clean-up and reorganization.

import os
import optparse
make_option = optparse.make_option

class Options:
    showwarning = 0
    objspace = "std" 
    oldstyle = 0
    uselibfile = 0
    nofaking = 0
    parser = "pypy" # "cpython" / "pypy" 
    compiler = "ast" 
         # "ast" uses interpreter/pyparser & interpreter/astcompiler.py 
         # "cpython" uses cpython parser and cpython c-level compiler 
    usemodules = []                        
    version = "2.4" # "native" / "2.3" / "2.4"

def run_tb_server(option, opt, value, parser):
    from pypy.tool import tb_server
    tb_server.start()

def get_standard_options():
    options = []

    def usemodules_callback(option, opt, value, parser): 
        parser.values.usemodules.append(value) 
        
    options.append(make_option(
        '-o', '--objspace', action="store", type="string", dest="objspace", 
        help="object space to run PyPy on."))
    options.append(make_option(
        '--usemodules', action="callback", metavar='NAME',
        callback=usemodules_callback,  type="string",
        help="(mixed) modules to use."))
    options.append(make_option(
        '--oldstyle', action="store_true", dest="oldstyle",
        help="enable oldstyle classes as default metaclass (std objspace only)"))
    options.append(make_option(
        '--uselibfile', action="store_true", dest="uselibfile",
        help="enable our custom file implementation"))
    options.append(make_option(
        '--nofaking', action="store_true", dest="nofaking",
        help="avoid faking of modules or objects"))
    options.append(make_option(
        '-w', action="store_true", dest="showwarning",
        help="enable warnings (disabled by default)"))
    options.append(make_option(
        '-H', action="callback",
        callback=run_tb_server,
        help="use web browser for traceback info"))
    options.append(make_option(
        '--compiler', action="store", type="string", dest="compiler",
        help="""select compiling approach. see pypy/doc/README.compiling""",
        metavar="[ast|cpython]")) 
    options.append(make_option(
        '--parser', action="store",type="string", dest="parser",
        help="select the parser module to use",
        metavar="[pypy|cpython]"))
## for this to work the option module need to be loaded before the grammar!
##     options.append(make_option(
##         '--version', action="store",type="string", dest="version",
##         help="select the Python version to emulate",
##         metavar="[native|2.3|2.4]"))

    return options

def process_options(optionlist, input_options, argv=None):
    global Options
    Options = input_options
    op = optparse.OptionParser()
    op.add_options(optionlist)
    options, args = op.parse_args(argv, input_options)
    return args
