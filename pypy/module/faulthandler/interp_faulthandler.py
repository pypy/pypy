import os

from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault


class FatalErrorState(object):
    def __init__(self, space):
        self.enabled = False

def enable(space):
    space.fromcache(FatalErrorState).enabled = True

def disable(space):
    space.fromcache(FatalErrorState).enabled = False

def is_enabled(space):
    return space.wrap(space.fromcache(FatalErrorState).enabled)

def register(space, __args__):
    pass


@unwrap_spec(w_file=WrappedDefault(None),
             w_all_threads=WrappedDefault(True))
def dump_traceback(space, w_file, w_all_threads):
    ec = space.getexecutioncontext()
    ecs = space.threadlocals.getallvalues()

    if space.is_none(w_file):
        w_file = space.sys.get('stderr')
    fd = space.c_filedescriptor_w(w_file)

    frame = ec.gettopframe()
    while frame:
        code = frame.pycode
        lineno = frame.get_last_lineno()
        if code:
            os.write(fd, "File \"%s\", line %s in %s\n" % (
                    code.co_filename, lineno, code.co_name))
        else:
            os.write(fd, "File ???, line %s in ???\n" % (
                    lineno,))

        frame = frame.f_backref()
 
