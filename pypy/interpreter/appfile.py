import os

class AppFile:
    """Dynamic loader of a set of Python functions and objects that
    should work at the application level (conventionally in .app.py files)"""

    # absolute name of the parent directory
    ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_PATH_EXT = [('appspace', '.py')]
    LOCAL_PATH = []

    def __init__(self, modulename, localpath=[]):
        "Load and compile the helper file."
        # XXX looking for a pre-compiled file here will be quite essential
        #     when we want to bootstrap the compiler

        # 'modulename' could be 'package.module' if passed in as __name__
        # we ignore that package part
        modulename = modulename.split('.')[-1]
        path_ext = [(path, '_app.py') for path in localpath + self.LOCAL_PATH]
        for path, ext in path_ext + self.DEFAULT_PATH_EXT:
            dirname = os.path.join(self.ROOTDIR, path.replace('.', os.sep))
            filename = os.path.join(dirname, modulename+ext)
            if os.path.exists(filename):
                break
        else:
            raise IOError, "cannot locate helper module '%s' in %s" % (
                modulename, path_ext)
        f = open(filename, 'r')
        src = f.read()
        f.close()
        #print filename
        self.bytecode = compile(src, filename, 'exec')


class Namespace:

    def __init__(self, space, w_namespace=None):
        self.space = space
        ec = space.getexecutioncontext()
        if w_namespace is None:
            w_namespace = ec.make_standard_w_globals()
        self.w_namespace = w_namespace

    def get(self, objname):
        "Returns a wrapped copy of an object by name."
        w_name = self.space.wrap(objname)
        w_obj = self.space.getitem(self.w_namespace, w_name)
        return w_obj

    def call(self, functionname, argumentslist):
        "Call a module function."
        w_function = self.get(functionname)
        w_arguments = self.space.newtuple(argumentslist)
        w_keywords = self.space.newdict([])
        return self.space.call(w_function, w_arguments, w_keywords)

    def runbytecode(self, bytecode):
        # initialize the module by running the bytecode in a new
        # dictionary, in a new execution context
        from pyframe import PyFrame
        from pycode import PyByteCode
        ec = self.space.getexecutioncontext()
        res = PyByteCode()
        res._from_code(bytecode)
        frame = PyFrame(self.space, res,
                                self.w_namespace, self.w_namespace)
        ec.eval_frame(frame)


class AppHelper(Namespace):

    def __init__(self, space, appfile, w_namespace=None):
        Namespace.__init__(self, space, w_namespace)
        self.runbytecode(appfile.bytecode)
