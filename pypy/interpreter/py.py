import autopath
from pypy.tool import option
from pypy.tool.optik import make_option
from pypy.interpreter import main, interactive, baseobjspace
import sys

class Options(option.Options):
    interactive = 0

def get_main_options():
    options = option.get_standard_options()
    options.append(make_option(
        '-i', action="store_true", dest="interactive"))
    return options

def main_(argv=None):
    args = option.process_options(get_main_options(), Options, argv[1:])
    space = option.objspace()
    if args:
        try:
            main.run_file(args[0], space)
        except baseobjspace.PyPyError, pypyerr:
            pypyerr.operationerr.print_detailed_traceback(pypyerr.space)
    else:
        con = interactive.PyPyConsole(space)
        con.interact()
        
        

if __name__ == '__main__':
    main_(sys.argv)
