import autopath
from pypy.interpreter import executioncontext, module, eval
from pypy.interpreter.error import OperationError
from pypy.interpreter.pycode import PyCode
import sys, types

def ensure__main__(space):
    w_main = space.wrap('__main__')
    w_modules = space.sys.get('modules')
    try:
        return space.getitem(w_modules, w_main)
    except OperationError, e:
        if not e.match(space, space.w_KeyError):
            raise
    mainmodule = module.Module(space, w_main)
    space.setitem(w_modules, w_main, mainmodule)
    return mainmodule

def compilecode(space, source, filename, cmd='exec'):
    if isinstance(source, types.CodeType):
        pycode = PyCode(space)._from_code(source)
    else:
        w = space.wrap
        w_code = space.builtin.call('compile', 
                 w(source), w(filename), w(cmd), w(0), w(0))
        pycode = space.interpclass_w(w_code)
    assert isinstance(pycode, eval.Code)
    return pycode


def _run_eval_string(source, filename, space, eval):
    if eval:
        cmd = 'eval'
    else:
        cmd = 'exec'
 
    try:
        if space is None:
            from pypy.objspace.std import StdObjSpace
            space = StdObjSpace()

        w = space.wrap

        pycode = compilecode(space, source, filename, cmd)

        mainmodule = ensure__main__(space)
        w_globals = mainmodule.w_dict

        space.setitem(w_globals, w('__builtins__'), space.builtin)

        retval = pycode.exec_code(space, w_globals, w_globals)
        if eval:
            return retval
        else:
            return

    except OperationError, operationerr:
        operationerr.record_interpreter_traceback()
        raise

def run_string(source, filename='<string>', space=None):
    _run_eval_string(source, filename, space, False)

def eval_string(source, filename='<string>', space=None):
    return _run_eval_string(source, filename, space, True)

def run_file(filename, space=None):
    if __name__=='__main__':
        print "Running %r with %r" % (filename, space)
    istring = open(filename).read()
    run_string(istring, filename, space)

# ____________________________________________________________

def run_toplevel_program(space, source, filename='<program>',
                         w_globals=None, verbose=False):
    """Run the given source code in the given globals (or __main__ by default).
    Intended use is to run the main program or one interactive statement.
    It handles details like forwarding exceptions to sys.excepthook(),
    catching SystemExit, printing a newline after sys.stdout if needed, etc.
    """
    try:
        # build a valid w_globals
        if w_globals is None:
            w_globals = ensure__main__(space).w_dict
        w1 = space.wrap('__builtins__')
        if not space.is_true(space.contains(w_globals, w1)):
            space.setitem(w_globals, w1, space.builtin)

        # compile and execute the code
        pycode = compilecode(space, source, filename)
        pycode.exec_code(space, w_globals, w_globals)

        # we arrive here if no exception is raised.  stdout cosmetics...
        try:
            w_stdout = space.sys.get('stdout')
            w_softspace = space.getattr(w_stdout, space.wrap('softspace'))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            # Don't crash if user defined stdout doesn't have softspace
        else:
            if space.is_true(w_softspace):
                space.call_method(w_stdout, 'write', space.wrap('\n'))

    except OperationError, operationerr:
        operationerr.normalize_exception(space)
        w_type = operationerr.w_type
        w_value = operationerr.w_value
        w_traceback = space.wrap(operationerr.application_traceback)

        # for debugging convenience we also insert the exception into
        # the interpreter-level sys.last_xxx
        operationerr.record_interpreter_traceback()
        sys.last_type, sys.last_value, sys.last_traceback = sys.exc_info()

        try:
            # exit if we catch a w_SystemExit
            if operationerr.match(space, space.w_SystemExit):
                w_exitcode = space.getattr(operationerr.w_value,
                                           space.wrap('code'))
                if space.is_w(w_exitcode, space.w_None):
                    exitcode = 0
                else:
                    try:
                        exitcode = space.int_w(w_exitcode)
                    except OperationError:
                        # not an integer: print it to stderr
                        msg = space.str_w(space.str(w_exitcode))
                        print >> sys.stderr, msg
                        exitcode = 1
                raise SystemExit(exitcode)

            # set the sys.last_xxx attributes
            space.setitem(space.sys.w_dict, space.wrap('last_type'), w_type)
            space.setitem(space.sys.w_dict, space.wrap('last_value'), w_value)
            space.setitem(space.sys.w_dict, space.wrap('last_traceback'),
                          w_traceback)

            # call sys.excepthook if present
            w_hook = space.sys.getdictvalue(space, 'excepthook')
            if w_hook is not None:
                # hack: skip it if it wasn't modified by the user,
                #       to do instead the faster verbose/nonverbose thing below
                w_original = space.sys.getdictvalue(space, '__excepthook__')
                if w_original is None or not space.is_w(w_hook, w_original):
                    space.call_function(w_hook, w_type, w_value, w_traceback)
                    return 1   # done

        except OperationError, err2:
            # XXX should we go through sys.get('stderr') ?
            print >> sys.stderr, 'Error calling sys.excepthook:'
            err2.print_application_traceback(space)
            print >> sys.stderr
            print >> sys.stderr, 'Original exception was:'

        # we only get here if sys.excepthook didn't do its job
        if verbose:
            operationerr.print_detailed_traceback(space)
        else:
            operationerr.print_application_traceback(space)
        return 1

    return 0   # success
