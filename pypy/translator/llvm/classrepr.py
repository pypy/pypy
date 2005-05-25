"""
The representations of classes and Exceptions live here. Classes are
implemented as structs.
"""

import autopath
import sets

from types import FunctionType

from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import ClassDef
from pypy.translator.llvm import llvmbc

from pypy.translator.llvm.representation import debug, LLVMRepr
from pypy.translator.llvm.representation import TmpVariableRepr
from pypy.translator.llvm.typerepr import TypeRepr, PointerTypeRepr
from pypy.translator.llvm.typerepr import SimpleTypeRepr
from pypy.translator.llvm.funcrepr import FunctionRepr, BoundMethodRepr
from pypy.translator.llvm.funcrepr import VirtualMethodRepr
from pypy.translator.llvm.memorylayout import MemoryLayout

debug = False
lazy_debug = False

class ClassRepr(TypeRepr):
    l_classes = {}
    def get(obj, gen):
        classdef = None
        if obj.__class__ is Constant:
            bind = gen.annotator.binding(obj)
            if bind.__class__ is annmodel.SomePBC and \
                gen.annotator.bookkeeper.userclasses.has_key(bind.const):
                classdef = gen.annotator.bookkeeper.userclasses[bind.const]
        elif isinstance(obj, annmodel.SomeInstance):
            classdef = obj.classdef
        elif isinstance(obj, ClassDef):
            classdef = obj
        if classdef is None:
            return None
        if (classdef, gen) not in ClassRepr.l_classes:
            ClassRepr.l_classes[(classdef, gen)] = ClassRepr(classdef, gen)
        return ClassRepr.l_classes[(classdef, gen)]
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "ClassRepr: %s, %s" % (obj, hex(id(self)))
        self.classdef = obj
        self.gen = gen
        self.includefile = ""
        self.name = gen.get_global_tmp("class.%s" % self.classdef.cls.__name__)
        self.objectname = gen.get_global_tmp("class.%s.object" %
                                             self.classdef.cls.__name__)
        if debug:
            print self.name
        assert ".Exception.object" not in self.objectname
        self.dependencies = sets.Set()

    lazy_attributes = ['l_base', 'memlayout', 'definition', 'methods']

    def setup(self):
        if debug:
            print "ClassRepr.setup()", id(self), hex(id(self))
            print len(ClassRepr.l_classes)
        gen = self.gen
        if self.classdef.basedef is not None: #get attributes from base classes
            #XXX if the base class is a builtin Exception we want the
            #ExceptionTypeRepr, not the ClassRepr
            if self.classdef.basedef.cls.__module__ == "exceptions":
                #XXX we want something more complicated here:
                #if the class has no __init__ function we need to insert the
                #'args' attribute the builtin exceptions have
                self.l_base = gen.get_repr(self.classdef.basedef.cls)
            else:
                self.l_base = gen.get_repr(self.classdef.basedef)
            assert self not in self.l_base.get_dependencies()
            self.dependencies.add(self.l_base)
        else:
            self.l_base = None
        attribs = []
        meth = []
        if debug:
            print "attributes", self.classdef.attrs
        #get attributes of this class and decide whether they are methods
        for key, attr in self.classdef.attrs.items():
            if debug:
                print key, attr, attr.sources, attr.s_value,
            if isinstance(attr.s_value, annmodel.SomeImpossibleValue):
                if debug:
                    print "--> removed"
                continue
            if len(attr.sources) != 0:
                func = self.classdef.cls.__dict__[attr.name]
                meth.append((key, func))
                if debug:
                    print "--> method1"
            elif isinstance(attr.s_value, annmodel.SomePBC) and \
               attr.s_value.knowntype is FunctionType:
                func = self.classdef.cls.__dict__[attr.name]
                meth.append((key, func))
                if debug:
                    print "--> method2"
            else:
                attribs.append(attr)
                if debug:
                    print "--> value"
        l_att_types = [gen.get_repr(attr.s_value) for attr in attribs]
        attribs = [attr.name for attr in attribs]
        self.dependencies.update(l_att_types)
        if self.l_base is not None:
            self.memlayout = self.l_base.memlayout.extend_layout(attribs,
                                                                 l_att_types)
            self.dependencies.update(self.l_base.memlayout.l_types)
        else:
            attribs = ["__class__"] + attribs
            l_att_types = [SimpleTypeRepr("%std.class*", gen)] + l_att_types
            self.memlayout = MemoryLayout(attribs, l_att_types, self.gen)
        self.definition = "%s = %s" % (self.name, self.memlayout.definition())
        self.methods = dict(meth)

    def get_globals(self):
        s = "\n%s = internal global %%std.class {%%std.class* null, uint %i}"
        s = s % (self.objectname, abs(id(self)) & 0xFFFFFFF)
        return self.definition + s

    def collect_init_code(self, lblock, l_func):
        if self.l_base is None:
            return
        l_tmp = self.gen.get_local_tmp(None, l_func)
        i = "%s = getelementptr %%std.class* %s, int 0, uint 0" % \
            (l_tmp.llvmname(), self.objectname)
        lblock.instruction(i)
        lblock.instruction("store %%std.class* %s, %%std.class** %s" %
                           (self.l_base.llvmname(), l_tmp.llvmname()))

    def llvmtype(self):
        return "%std.class*"

    def llvmname(self):
        return self.objectname

    def op_simple_call(self, l_target, args, lblock, l_func):
        lblock.malloc(l_target, self)
        self.memlayout.set(l_target, "__class__", self, lblock, l_func)
        init = None
        for clsd in self.classdef.getmro():
            if ("__init__" in clsd.cls.__dict__ and
                clsd.cls.__module__ != "exceptions"):
                init = clsd.cls.__dict__["__init__"]
                break
        if init is not None:
            l_init = self.gen.get_repr(init)
            l_func.dependencies.add(l_init)
            l_tmp = self.gen.get_local_tmp(PointerTypeRepr("sbyte", self.gen),
                                           l_func)
            l_func.dependencies.add(l_tmp)
            #XXX VirtualMethodRepr should recognize __init__ methods
            if isinstance(l_init, VirtualMethodRepr):
                l_init = l_init.l_funcs[l_init.l_classes.index(self)]
            l_init.op_simple_call(l_tmp, [l_init, l_target] + args[1:],
                                  lblock, l_func)

    def t_op_getattr(self, l_target, args, lblock, l_func):
        if debug:
            print "t_op_getattr of ClassRepr called", l_target, args, self.name
        if not isinstance(args[1], Constant):
            raise CompileError,"getattr called with non-constant: %s" % args[1]
        if args[1].value in self.memlayout.attrs:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            self.memlayout.get(l_target, l_args0, args[1].value, lblock,
                               l_func)
            return
        else:
            if debug:
                print list(self.classdef.getmro())
            for cls in self.classdef.getmro():
                l_cls = self.gen.get_repr(cls)
                if l_cls != self:
                    self.dependencies.add(l_cls)
                if args[1].value in l_cls.methods:
                    if debug:
                        print "class %s, %s matches" % (cls, l_cls)
                    l_args0 = self.gen.get_repr(args[0])
                    l_func.dependencies.add(l_args0)
                    l_method = BoundMethodRepr(l_target.type, l_args0,
                                               self.gen)
                    l_func.dependencies.add(l_method)
                    l_method.setup()
                    l_target.type = l_method
                    return
        raise CompileError, ("getattr called with unknown attribute %s" % \
                             args[1].value)

    def t_op_setattr(self, l_target, args, lblock, l_func):
        if not isinstance(args[1], Constant):
            raise CompileError,"setattr called with non-constant: %s" % args[1]
        if args[1].value not in self.memlayout.attr_num:
            raise CompileError, ("setattr called with unknown attribute %s" % \
                                 args[1].value)
        l_args0 = self.gen.get_repr(args[0])
        l_value = self.gen.get_repr(args[2])
        l_func.dependencies.update([l_args0, l_value])
        self.memlayout.set(l_args0, args[1].value, l_value, lblock, l_func)

    def t_op_type(self, l_target, args, lblock, l_func):
        l_args0 = self.gen.get_repr(args[0])
        l_func.dependencies.add(l_args0)
        self.memlayout.get(l_target, l_args0, "__class__", lblock, l_func)

    def iter_subclasses(self):
        for cls, classdef in self.classdef.subdefs.iteritems():
            l_cls = self.gen.get_repr(classdef)
            yield l_cls
            for l_c in l_cls.iter_subclasses():
                yield l_c

def create_builtin_exceptions(gen, dependencies):
    import exceptions
    for exc in ["IndexError"]:
        if "__" not in exc:
            l_exc = gen.get_repr(getattr(exceptions, exc))
            dependencies.add(l_exc)

class ExceptionTypeRepr(TypeRepr):
    def get(obj, gen):
        try:
            if isinstance(obj, Constant):
                if issubclass(obj.value, Exception):
                    return ExceptionTypeRepr(obj.value, gen)
                return None
            elif issubclass(obj, Exception):
                return ExceptionTypeRepr(obj, gen)
        except TypeError:
            pass
        return None
    get = staticmethod(get)

    def __init__(self, exception, gen):
        if debug:
            print "ExceptionTypeRepr: %s" % exception
        self.gen = gen
        self.exception = exception
        self.name = "%std.exception"
        self.objectname = gen.get_global_tmp("class.%s.object" %
                                             self.exception.__name__)
        s = "%s = internal global %%std.class {%%std.class* null, uint %i}"
        self.definition = s % (self.objectname, abs(id(exception)) & 0xFFFFFFF)
        self.dependencies = sets.Set()

    lazy_attributes = ['l_base', 'memlayout']

    def setup(self):
        if len(self.exception.__bases__) != 0:
            self.l_base = self.gen.get_repr(self.exception.__bases__[0])
            self.dependencies.add(self.l_base)
        else:
            self.l_base = None
        attribs = ["__class__", "args"]
        l_att_types = [SimpleTypeRepr("%std.class*", self.gen),
                       self.gen.get_repr(annmodel.SomeString())]
        self.memlayout = MemoryLayout(attribs, l_att_types, self.gen)

    def typename(self):
        return "%std.exception*"

    def llvmtype(self):
        return "%std.class*"

    def llvmname(self):
        return self.objectname

    def typed_name(self):
        return "%%std.class* %s" % self.objectname

    def collect_init_code(self, lblock, l_func):
        if self.l_base is None:
            return
        l_tmp = self.gen.get_local_tmp(None, l_func)
        i = "%s = getelementptr %%std.class* %s, int 0, uint 0" % \
            (l_tmp.llvmname(), self.objectname)
        lblock.instruction(i)
        lblock.instruction("store %%std.class* %s, %%std.class** %s" %
                           (self.l_base.llvmname(), l_tmp.llvmname()))

    def op_simple_call(self, l_target, args, lblock, l_func):
        lblock.malloc(l_target)
        l_args0 = self.gen.get_repr(args[0])
        l_tmp = self.gen.get_local_tmp(PointerTypeRepr("%std.class*",
                                                       self.gen), l_func)
        l_func.dependencies.update([l_args0, l_tmp])
        lblock.getelementptr(l_tmp, l_target, [0, 0])
        lblock.store(l_args0, l_tmp)
        if len(args) > 1:
            l_args1 = self.gen.get_repr(args[1])
        else:
            l_args1 = self.gen.get_repr(Constant(None))
        l_tmp1 = self.gen.get_local_tmp(PointerTypeRepr("%std.list.sbyte*",
                                                        self.gen), l_func)
        l_cast = self.gen.get_local_tmp(PointerTypeRepr("%std.list.sbyte",
                                                        self.gen), l_func)
        l_func.dependencies.update([l_args1, l_tmp1])
        lblock.getelementptr(l_tmp1, l_target, [0, 1])
        lblock.cast(l_cast, l_args1)
        lblock.store(l_cast, l_tmp1)

    def t_op_type(self, l_target, args, lblock, l_func):
        l_args0 = self.gen.get_repr(args[0])
        l_func.dependencies.add(l_args0)
        l_tmp = self.gen.get_local_tmp(
            PointerTypeRepr("%std.class*", self.gen), l_func)
        lblock.getelementptr(l_tmp, l_args0, [0, 0])
        lblock.load(l_target, l_tmp)
    

class InstanceRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant):
            ann = gen.annotator.binding(obj)
            if isinstance(ann, annmodel.SomeInstance):
                return InstanceRepr(obj, ann.classdef, gen)
    get = staticmethod(get)

    def __init__(self, obj, classdef, gen):
        if debug:
            print "InstanceRepr: ", obj, classdef
        self.obj = obj
        self.gen = gen
        self.type = gen.get_repr(classdef)
        self.dependencies = sets.Set([self.type])
        self.name = gen.get_global_tmp(obj.value.__class__.__name__ + ".inst")

    lazy_attributes = ['l_attrib_values', 'definition']

    def setup(self):
        self.l_attrib_values = [self.type]
        for attr in self.type.memlayout.attrs[1:]:
            s_a = self.gen.get_repr(getattr(self.obj.value, attr))
            self.l_attrib_values.append(s_a)
        self.dependencies.update(self.l_attrib_values)
        self.definition = self.name + \
                          " = internal global %s" % self.llvmtype()[:-1] + \
                          self.type.memlayout.constant(self.l_attrib_values)

    def get_globals(self):
        return self.definition

    def __getattr__(self, name):
        if name.startswith("op_"):
            return getattr(self.type, "t_" + name, None)
        else:
            raise AttributeError, ("InstanceRepr instance has no attribute %s"
                                   % repr(name))
