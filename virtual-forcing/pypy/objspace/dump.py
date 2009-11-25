import os
from pypy.objspace.proxy import patch_space_in_place
from pypy.objspace.std.objspace import StdObjSpace, W_Object
from pypy.interpreter.error import OperationError
from pypy.interpreter import baseobjspace

DUMP_FILE_NAME = 'pypy-space-dump'
DUMP_FILE_MODE = 0600

class Dumper(object):
    dump_fd = -1

    def __init__(self, space):
        self.space = space
        self.dumpspace_reprs = {}

    def open(self):
        space = self.space
        self.dumpspace_reprs.update({
            space.w_None:  'None',
            space.w_False: 'False',
            space.w_True:  'True',
            })
        if self.dump_fd < 0:
            self.dump_fd = os.open(DUMP_FILE_NAME,
                                   os.O_WRONLY|os.O_CREAT|os.O_TRUNC,
                                   DUMP_FILE_MODE)

    def close(self):
        if self.dump_fd >= 0:
            os.close(self.dump_fd)
            self.dump_fd = -1
        self.dumpspace_reprs.clear()

    def dump_get_repr(self, w_obj):
        try:
            return self.dumpspace_reprs[w_obj]
        except KeyError:
            saved_fd = self.dump_fd
            try:
                self.dump_fd = -1
                space = self.space
                if isinstance(w_obj, W_Object):
                    w_type = space.type(w_obj)
                else:
                    w_type = None
                if w_type is space.w_int:
                    n = space.int_w(w_obj)
                    s = str(n)
                elif w_type is space.w_str:
                    s = space.str_w(w_obj)
                    digit2hex = '0123456789abcdef'
                    lst = ["'"]
                    for c in s:
                        if c == '\\':
                            lst.append('\\')
                        if c >= ' ':
                            lst.append(c)
                        else:
                            lst.append('\\')
                            if c == '\n':
                                lst.append('n')
                            elif c == '\t':
                                lst.append('t')
                            else:
                                lst.append('x')
                                lst.append(digit2hex[ord(c) >> 4])
                                lst.append(digit2hex[ord(c) & 0xf])
                    lst.append("'")
                    s = ''.join(lst)
                elif w_type is space.w_float:
                    n = space.float_w(w_obj)
                    s = str(n)
                else:
                    s = '%s at 0x%x' % (w_obj, id(w_obj))
                self.dumpspace_reprs[w_obj] = s
            finally:
                self.dump_fd = saved_fd
            return s

    def dump_enter(self, opname, args_w):
        if self.dump_fd >= 0:
            text = '\t'.join([self.dump_get_repr(w_arg) for w_arg in args_w])
            os.write(self.dump_fd, '%s CALL   %s\n' % (opname, text))

    def dump_returned_wrapped(self, opname, w_obj):
        if self.dump_fd >= 0:
            s = self.dump_get_repr(w_obj)
            os.write(self.dump_fd, '%s RETURN %s\n' % (opname, s))

    def dump_returned(self, opname):
        if self.dump_fd >= 0:
            os.write(self.dump_fd, '%s RETURN\n' % (opname,))

    def dump_raised(self, opname, e):
        if self.dump_fd >= 0:
            if isinstance(e, OperationError):
                s = e.errorstr(self.space)
            else:
                s = '%s' % (e,)
            os.write(self.dump_fd, '%s RAISE  %s\n' % (opname, s))


# for now, always make up a wrapped StdObjSpace
class DumpSpace(StdObjSpace):

    def __init__(self, *args, **kwds):
        self.dumper = Dumper(self)
        StdObjSpace.__init__(self, *args, **kwds)
        patch_space_in_place(self, 'dump', proxymaker)

    def _freeze_(self):
        # remove strange things from the caches of self.dumper
        # before we annotate
        self.dumper.close()
        return StdObjSpace._freeze_(self)

    def startup(self):
        StdObjSpace.startup(self)
        self.dumper.open()

    def finish(self):
        self.dumper.close()
        StdObjSpace.finish(self)

    def wrap(self, x):
        w_res = StdObjSpace.wrap(self, x)
        self.dumper.dump_returned_wrapped('           wrap', w_res)
        return w_res
    wrap._annspecialcase_ = "specialize:wrap"


Space = DumpSpace

# __________________________________________________________________________

nb_args = {}
op_returning_wrapped = {}

def setup():
    nb_args.update({
        # ---- irregular operations ----
        'wrap': 0,
        'str_w': 1,
        'int_w': 1,
        'float_w': 1,
        'uint_w': 1,
        'unicode_w': 1,
        'bigint_w': 1,
        'interpclass_w': 1,
        'unwrap': 1,
        'is_true': 1,
        'is_w': 2,
        'newtuple': 0,
        'newlist': 0,
        'newdict': 0,
        'newslice': 0,
        'call_args': 1,
        'marshal_w': 1,
        'log': 1,
        })
    op_returning_wrapped.update({
        'wrap': True,
        'newtuple': True,
        'newlist': True,
        'newdict': True,
        'newslice': True,
        'call_args': True,
        })
    for opname, _, arity, _ in baseobjspace.ObjSpace.MethodTable:
        nb_args.setdefault(opname, arity)
        op_returning_wrapped[opname] = True
    for opname in baseobjspace.ObjSpace.IrregularOpTable:
        assert opname in nb_args, "missing %r" % opname

setup()
del setup

# __________________________________________________________________________

def proxymaker(space, opname, parentfn):
    if opname == 'wrap':
        return None
    returns_wrapped = opname in op_returning_wrapped
    aligned_opname = '%15s' % opname
    n = nb_args[opname]
    def proxy(*args, **kwds):
        dumper = space.dumper
        args_w = list(args[:n])
        dumper.dump_enter(aligned_opname, args_w)
        try:
            res = parentfn(*args, **kwds)
        except Exception, e:
            dumper.dump_raised(aligned_opname, e)
            raise
        else:
            if returns_wrapped:
                dumper.dump_returned_wrapped(aligned_opname, res)
            else:
                dumper.dump_returned(aligned_opname)
            return res
    proxy.func_name = 'proxy_%s' % (opname,)
    return proxy
