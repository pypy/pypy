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
        con = interactive.PyPyConsole(space)
        con.interact()
        

if __name__ == '__main__':
    main_(sys.argv)
