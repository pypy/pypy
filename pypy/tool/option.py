import os
from pypy.tool import optik
make_option = optik.make_option

class Options:
    verbose = 0
    showwarning = 0
    spaces = []    

def get_standard_options():
    options = []

    def objspace_callback(option, opt, value, parser, space):
        parser.values.spaces.append(space)

    options.append(make_option(
        '-S', action="callback",
        callback=objspace_callback, callback_args=("std",),
        help="run in std object space"))
    options.append(make_option(
        '-T', action="callback",
        callback=objspace_callback, callback_args=("trivial",),
        help="run in trivial object space"))
    options.append(make_option(
        '-A', action="callback",
        callback=objspace_callback, callback_args=("ann",),
        help="run in annotation object space"))
    options.append(make_option(
        '-v', action="count", dest="verbose",
        help="verbose"))
    options.append(make_option(
        '-w', action="store_true", dest="showwarning",
        help="enable warnings (disabled by default)"))

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
            name = os.environ.get('OBJSPACE', 'trivial')
    
    try:
        return _spacecache[name]
    except KeyError:
        module = __import__("pypy.objspace.%s" % name, None, None, ["Space"])
        Space = module.Space
        return _spacecache.setdefault(name, Space())
