#!/usr/bin/env python 

try:
    import autopath
except ImportError:
    pass

from pypy.tool import option
from pypy.tool.optik import make_option
from pypy.interpreter import main, interactive, error
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
    from pypy.tool import tb_server
    args = option.process_options(get_main_options(), Options, argv[1:])
    space = None
    try:
        space = option.objspace()
        go_interactive = Options.interactive
        banner = ''
        if Options.command:
            args = ['-c']
        for arg in args:
            space.call_method(space.sys.w_argv, 'append', space.wrap(arg))
        if Options.command:
            try:
                main.run_string(Options.command[0], '<string>', space)
            except error.PyPyError, pypyerr:
                pypyerr.operationerr.print_detailed_traceback(pypyerr.space)
        elif args:
            try:
                main.run_file(args[0], space)
            except error.PyPyError, pypyerr:
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
    except:
        exc_type, value, tb = sys.exc_info()
        sys.last_type = exc_type
        sys.last_value = value
        sys.last_traceback = tb
        if issubclass(exc_type, SystemExit):
            pass   # don't print tracebacks for SystemExit
        elif isinstance(value, error.OperationError):
            value.print_detailed_traceback(space=space)
        else:
            sys.excepthook(exc_type, value, tb)
        tb_server.wait_until_interrupt()
            
    tb_server.stop()

if __name__ == '__main__':
    try:
        import readline
    except:
        pass
    main_(sys.argv)
