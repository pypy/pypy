import autopath
from pypy.tool import option
from pypy.tool.optik import make_option
from pypy.interpreter import main, interactive, baseobjspace
import sys

class Options(option.Options):
    interactive = 0
    command = []

def get_main_options():
    options = option.get_standard_options()
    options.append(make_option(
        '-i', action="store_true", dest="interactive",
        help="inspect interactively after running script"))
    
    def command_callback(option, opt, value, parser):
        parser.values.command = parser.rargs[:]
        parser.rargs[:] = []
        
    options.append(make_option(
        '-c', action="callback",
        callback=command_callback,
        help="program passed in as CMD (terminates option list)"))
        
    return options

def main_(argv=None):
    args = option.process_options(get_main_options(), Options, argv[1:])
    space = option.objspace()
    go_interactive = Options.interactive
    banner = ''
    if Options.command:
        try:
            main.run_string(Options.command[0], '<string>', space)
        except baseobjspace.PyPyError, pypyerr:
            pypyerr.operationerr.print_detailed_traceback(pypyerr.space)
    elif args:
        try:
            main.run_file(args[0], space)
        except baseobjspace.PyPyError, pypyerr:
            pypyerr.operationerr.print_detailed_traceback(pypyerr.space)
    else:
        go_interactive = 1
        banner = None
    if go_interactive:
        con = interactive.PyPyConsole(space)
        if banner == '':
            banner = '%s / %s'%(con.__class__.__name__,
                                space.__class__.__name__)
        con.interact(banner)

if __name__ == '__main__':
    main_(sys.argv)
