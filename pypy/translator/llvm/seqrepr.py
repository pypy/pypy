import autopath
import sets

from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel

from pypy.translator.llvm.representation import debug, LLVMRepr
from pypy.translator.llvm.typerepr import TypeRepr, IntTypeRepr
from pypy.translator.llvm.typerepr import PointerTypeRepr
from pypy.translator.llvm.funcrepr import BoundMethodRepr


class ListTypeRepr(TypeRepr):
    l_listtypes = {}
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeList:
            if (obj.s_item.__class__, gen) in ListTypeRepr.l_listtypes:
                return ListTypeRepr.l_listtypes[(obj.s_item.__class__, gen)]
            l_repr = ListTypeRepr(obj, gen)
            ListTypeRepr.l_listtypes[(obj.s_item.__class__, gen)] = l_repr
            return l_repr
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "ListTypeRepr: %s, %s" % (obj, obj.s_item)
        self.gen = gen
        self.l_itemtype = gen.get_repr(obj.s_item)
        self.dependencies = sets.Set([self.l_itemtype])
        itemtype = self.l_itemtype.llvmname()
        self.name = "%%std.list.%s" % itemtype.strip("%").replace("*", "")
        self.definition = self.name + " = type {uint, %s*}" % itemtype

    def get_functions(self):
        f = file(autopath.this_dir + "/list_template.ll", "r")
        s = f.read()
        f.close()
        itemtype = self.l_itemtype.llvmname()
        s = s.replace("%(item)s", self.l_itemtype.llvmname())
        s = s.replace("%(name)s", itemtype.strip("%").replace("*", ""))
        if isinstance(self.l_itemtype, IntTypeRepr):
            f1 = file(autopath.this_dir + "/int_list.ll", "r")
            s += f1.read()
            f1.close()
        return s

    def t_op_getitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "getitem", l_args)

    def t_op_setitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "setitem", l_args)

    def t_op_delitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "delitem", l_args)

    def t_op_getattr(self, l_target, args, lblock, l_func):
        if isinstance(args[1], Constant) and \
               args[1].value in ["append", "reverse", "pop"]:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            l_method = BoundMethodRepr(l_target.type, l_args0, self, self.gen)
            l_method.setup()
            l_target.type = l_method
        else:
            raise CompileError, "List method %s not supported." % args[1].value

class TupleTypeRepr(TypeRepr):
    def get(obj, gen):
        if isinstance(obj, annmodel.SomeTuple):
            return TupleTypeRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        self.gen = gen
        self.l_itemtypes = [gen.get_repr(l) for l in obj.items]
        self.name = (("{" + ", ".join(["%s"] * len(self.l_itemtypes)) + "}") %
                     tuple([l.llvmname() for l in self.l_itemtypes]))

    def get_functions(self):
        s = ("internal int %%std.len(%s %%t) {\n\tret int %i\n}\n" %
             (self.llvmname(), len(self.l_itemtypes)))
        return s

    def t_op_newtuple(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.malloc(l_target, self)
        l_ptrs = [self.gen.get_local_tmp(\
            PointerTypeRepr(l.llvmname(),self.gen), l_func)
                  for l in self.l_itemtypes]
        l_func.dependencies.update(l_ptrs)
        for i, l in enumerate(self.l_itemtypes):
            lblock.getelementptr(l_ptrs[i], l_target, [0, i])
            lblock.store(l_args[i], l_ptrs[i])

    def t_op_getitem(self, l_target, args, lblock, l_func):
        if not isinstance(args[1], Constant):
            raise CompileError, "index for tuple's getitem has to be constant"
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        l_tmp = self.gen.get_local_tmp(PointerTypeRepr(l_target.llvmtype(),
                                                       self.gen), l_func)
        cast = getattr(l_args[1], "cast_to_unsigned", None)
        if cast is not None:
            l_unsigned = cast(l_args[1], lblock, l_func)
        else:
            raise CompileError, "Invalid arguments to getitem"
        lblock.getelementptr(l_tmp, l_args[0], [0, l_unsigned])
        lblock.load(l_target, l_tmp)
