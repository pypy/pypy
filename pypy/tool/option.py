from pypy.tool import optik
make_option = optik.make_option

class Options:
    verbose = 0
    spacename = ''
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
        '-v', action="count", dest="verbose"))
    options.append(make_option(
        '-w', action="store_true", dest="showwarning"))

    return options

def process_options(optionlist, argv=None, v=None):
    op = optik.OptionParser()
    op.add_options(optionlist)
    options, args = op.parse_args(argv, v)
    if not options.spaces:
        options.spaces = ['trivial']
    return args
