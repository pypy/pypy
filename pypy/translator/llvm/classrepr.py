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
from pypy.translator.llvm.funcrepr import FunctionRepr, BoundMethodRepr
from pypy.translator.llvm.funcrepr import VirtualMethodRepr

debug = True

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
        if ".Exception.object" in self.objectname:
            1/0
        self.dependencies = sets.Set()
        self.setup_done = False
        self.attr_num = {}

    def setup(self):
        if self.setup_done:
            return
        self.setup_done = True
        if debug:
            print "ClassRepr.setup()", id(self), hex(id(self)), self.setup_done
            print len(ClassRepr.l_classes)
        gen = self.gen
        if self.classdef.basedef is not None: #get attributes from base classes
            #XXX if the base class is a builtin Exception we want the
            #ExceptionTypeRepr, not the ClassRepr
            if self.classdef.basedef.cls.__module__ == "exceptions":
                self.l_base = gen.get_repr(self.classdef.basedef.cls)
                #XXX we want something more complicated here:
                #if the class has no __init__ function we need to insert the
                #'args' attribute the builtin exceptions have
                attribs = []
            else:
                self.l_base = gen.get_repr(self.classdef.basedef)
                attribs = self.l_base.attributes
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
        self.l_attrs_types = [gen.get_repr(attr.s_value) for attr in attribs]
        self.dependencies = sets.Set(self.l_attrs_types)
        attributes = ", ".join([at.typename() for at in self.l_attrs_types])
        if attributes != "":
            self.definition = "%s = type {%%std.class*, %s}" % (self.name,
                                                                attributes)
        else:
            self.definition = "%s = type {%%std.class*}" % self.name
        self.attributes = attribs
        self.attr_num = {}
        for i, attr in enumerate(attribs):
            self.attr_num[attr.name] = i + 1
        self.methods = dict(meth)

    def get_globals(self):
        s = "\n%s = internal global %%std.class {%%std.class* null, uint %i}"
        s = s % (self.objectname, abs(id(self)))
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
        l_tmp = self.gen.get_local_tmp(
            PointerTypeRepr("%std.class*", self.gen), l_func)
        lblock.getelementptr(l_tmp, l_target, [0, 0])
        lblock.instruction("store %%std.class* %s, %s" %
                           (self.objectname, l_tmp.typed_name()))        
        init = None
        for cls in self.classdef.getmro():
            if "__init__" in cls.attrs:
                init = cls.attrs["__init__"].getvalue()
                break
        if init is not None:
            l_init = self.gen.get_repr(init)
            l_func.dependencies.add(l_init)
            l_args = [self.gen.get_repr(arg) for arg in args[1:]]
            self.dependencies.update(l_args)
            # XXX
            if isinstance(l_init, VirtualMethodRepr):
                l_init = l_init.l_funcs[l_init.l_classes.index(self)]
            lblock.call_void(l_init, [l_target] + l_args)

    def t_op_getattr(self, l_target, args, lblock, l_func):
        if debug:
            print "t_op_getattr of ClassRepr called", l_target, args, self.name
        if not isinstance(args[1], Constant):
            raise CompileError,"getattr called with non-constant: %s" % args[1]
        if args[1].value in self.attr_num:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            l_pter = self.gen.get_local_tmp(
                PointerTypeRepr(l_target.llvmtype(), self.gen), l_func)
            lblock.getelementptr(l_pter, l_args0,
                                 [0, self.attr_num[args[1].value]])
            lblock.load(l_target, l_pter)
            return
        else:
            if debug:
                print list(self.classdef.getmro())
            for cls in self.classdef.getmro():
                l_cls = self.gen.get_repr(cls)
                self.dependencies.add(l_cls)
                if args[1].value in l_cls.methods:
                    if debug:
                        print "class %s, %s matches" % (cls, l_cls)
                    l_args0 = self.gen.get_repr(args[0])
                    l_func.dependencies.add(l_args0)
                    l_method = BoundMethodRepr(l_target.type, l_args0, l_cls,
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
        if args[1].value in self.attr_num:
            l_type = self.l_attrs_types[self.attr_num[args[1].value] - 1]
            l_args0 = self.gen.get_repr(args[0])
            l_value = self.gen.get_repr(args[2])
            self.dependencies.update([l_args0, l_value])
            if l_value.llvmtype() != l_type.typename():
                l_cast = self.gen.get_local_tmp(l_type, l_func)
                self.dependencies.add(l_cast)
                lblock.cast(l_cast, l_value)
                l_value = l_cast
            l_pter = self.gen.get_local_tmp(
                PointerTypeRepr(l_value.llvmtype(), self.gen), l_func)
            lblock.getelementptr(l_pter, l_args0,
                                 [0, self.attr_num[args[1].value]])
            lblock.store(l_value, l_pter)
        else:
            raise CompileError, ("setattr called with unknown attribute %s" % \
                                 args[1].value)

    def t_op_type(self, l_target, args, lblock, l_func):
        l_args0 = self.gen.get_repr(args[0])
        l_func.dependencies.add(l_args0)
        l_tmp = self.gen.get_local_tmp(
            PointerTypeRepr("%std.class*", self.gen), l_func)
        lblock.getelementptr(l_tmp, l_args0, [0, 0])
        lblock.load(l_target, l_tmp)
        

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
        self.definition = s % (self.objectname, abs(id(exception)))
        self.dependencies = sets.Set()

    def setup(self):
        if len(self.exception.__bases__) != 0:
            self.l_base = self.gen.get_repr(self.exception.__bases__[0])
            self.dependencies.add(self.l_base)
        else:
            self.l_base = None

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
            print "InstanceRepr.get: ", obj, ann, ann.__class__
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

    def setup(self):
        self.l_attrib_values = []
        for attr in self.type.attributes:
            s_a = self.gen.get_repr(getattr(self.obj.value, attr.name))
            self.l_attrib_values.append(s_a)
        self.dependencies.update(self.l_attrib_values)
        self.definition = self.name + " = internal global %s {%s" % \
                          (self.llvmtype()[:-1], self.type.typed_name())
        if len(self.l_attrib_values) == 0:
            self.definition += "}"
        else:
            attrs = ", ".join([at.typename() + " " + av.llvmname()
                               for at, av in zip(self.type.l_attrs_types,
                                                 self.l_attrib_values)])
            self.definition += ", " + attrs + "}"

    def get_globals(self):
        return self.definition

    def __getattr__(self, name):
        if name.startswith("op_"):
            return getattr(self.type, "t_" + name, None)
        else:
            raise AttributeError, ("InstanceRepr instance has no attribute %s"
                                   % repr(name))
