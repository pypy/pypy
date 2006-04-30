import types

from pypy.tool.udir import udir
from pypy.objspace.flow.model import Constant, c_last_exception
from pypy.translator.translator import graphof
from pypy.rpython.ootypesystem.ootype import dynamicType, oodowncast, List, Record, Instance, _class, _static_meth, _meth, ROOT
from pypy.rpython.ootypesystem.rclass import OBJECT
from pypy.translator.cl.clrepr import clrepr

class InsertionOrderedDict(dict):
    def __init__(self):
        super(InsertionOrderedDict, self).__init__()
        self.ordered_keys = []

    def __setitem__(self, key, val):
        super(InsertionOrderedDict, self).__setitem__(key, val)
        if key not in self.ordered_keys:
            self.ordered_keys.append(key)

    def values(self):
        return [self[key] for key in self.ordered_keys]

class Op:

    def __init__(self, gen, op):
        self.gen = gen
        self.op = op
        self.opname = op.opname
        self.args = op.args
        self.result = op.result

    def __iter__(self):
        method = getattr(self, "op_" + self.opname)
        result = clrepr(self.result)
        args = map(self.gen.check_declaration, self.args)
        for line in method(result, *args):
            yield line

    def nop(self, result, arg):
        yield "(setf %s %s)" % (clrepr(result, True), clrepr(arg, True))

    op_same_as = nop
    op_ooupcast = nop
    op_oodowncast = nop

    def make_unary_op(cl_op):
        def _(self, result, arg):
            yield "(setf %s (%s %s))" % (clrepr(result, True),
                                         cl_op,
                                         clrepr(arg, True))
        return _

    op_bool_not = make_unary_op("not")
    op_cast_char_to_int = make_unary_op("char-code")
    op_cast_int_to_char = make_unary_op("code-char")
    op_cast_float_to_int = make_unary_op("truncate")
    op_cast_int_to_float = make_unary_op("float")

    def make_binary_op(cl_op):
        def _(self, result, arg1, arg2):
            yield "(setf %s (%s %s %s))" % (clrepr(result, True),
                                            cl_op,
                                            clrepr(arg1, True),
                                            clrepr(arg2, True))
        return _

    op_int_add = make_binary_op("+")
    op_int_mul = make_binary_op("*")
    op_int_eq = make_binary_op("=")
    op_int_gt = make_binary_op(">")
    op_int_ge = make_binary_op(">=")
    op_int_lt = make_binary_op("<")
    op_int_le = make_binary_op("<=")
    op_int_and = make_binary_op("logand")
    op_int_mod = make_binary_op("mod")
    op_int_sub = make_binary_op("-")
    op_float_sub = make_binary_op("-")
    op_float_truediv = make_binary_op("/")
    op_char_eq = make_binary_op("char=")
    op_char_le = make_binary_op("char<=")
    op_char_ne = make_binary_op("char/=")

    def op_int_is_true(self, result, arg):
        yield "(setf %s (not (zerop %s)))" % (clrepr(result, True),
                                              clrepr(arg, True))

    def op_direct_call(self, result, fun, *args):
        funobj = self.args[0].value
        self.gen.pendinggraphs.append(funobj)
        args = " ".join(args)
        yield "(setf %s (%s %s))" % (clrepr(result, True),
                                     clrepr(fun, True),
                                     clrepr(args, True))

    def op_new(self, result, clsname):
        cls = self.args[0].value
        if isinstance(cls, List):
            yield "(setf %s (make-array 0 :adjustable t))" % (clrepr(result, True),)
        elif isinstance(cls, Record):
            clsname = self.gen.declare_struct(cls)
            yield "(setf %s (make-%s))" % (clrepr(result, True),
                                           clrepr(clsname, True))
        elif isinstance(cls, Instance):
            clsname = clrepr(cls)
            if self.gen.is_exception_instance(cls):
                self.gen.declare_exception(cls)
                yield "(setf %s (make-condition %s))" % (result, clsname)
            else:
                self.gen.declare_class(cls)
                yield "(setf %s (make-instance %s))" % (result, clsname)
        else:
            raise NotImplementedError()

    def op_runtimenew(self, result, arg):
        yield "(setf %s (make-instance %s))" % (clrepr(result, True),
                                                clrepr(arg, True))

    def op_instanceof(self, result, arg, clsname):
        clsname = clrepr(self.args[1].value)
        yield "(setf %s (typep %s %s))" % (clrepr(result, True),
                                           clrepr(arg, True),
                                           clrepr(clsname, True))

    def op_oosend(self, result, *ignore):
        method = self.args[0].value
        receiver = self.args[1]
        cls = receiver.concretetype
        args = self.args[2:]
        if isinstance(cls, List):
            impl = ListImpl(receiver)
            code = getattr(impl, method)(*args)
            yield "(setf %s %s)" % (clrepr(result, True), clrepr(code, True))
        elif isinstance(cls, Instance):
            name = clrepr(method, symbol=True)
            selfvar = clrepr(receiver)
            args = map(self.gen.check_declaration, args)
            args = " ".join(args)
            if args:
                yield "(setf %s (%s %s %s))" % (clrepr(result, True),
                                                clrepr(name, True),
                                                clrepr(selfvar, True),
                                                clrepr(args, True))
            else:
                yield "(setf %s (%s %s))" % (clrepr(result, True),
                                             clrepr(name, True),
                                             clrepr(selfvar, True))

    def op_oogetfield(self, result, obj, _):
        fieldname = self.args[1].value
        if isinstance(self.args[0].concretetype, Record):
            yield "(setf %s (slot-value %s '%s))" % (clrepr(result, True),
                                                   clrepr(obj, True),
                                                   clrepr(fieldname, True))
        else:
            yield "(setf %s (%s %s))" % (clrepr(result, True),
                                         clrepr(fieldname, True),
                                         clrepr(obj, True))

    def op_oosetfield(self, result, obj, _, value):
        fieldname = self.args[1].value
        if isinstance(self.args[0].concretetype, Record):
            yield "(setf (slot-value %s '%s) %s)" % (clrepr(obj, True),
                                                     clrepr(fieldname, True),
                                                     clrepr(value, True))
        else:
            yield "(setf (%s %s) %s)" % (clrepr(fieldname, True),
                                         clrepr(obj, True),
                                         clrepr(value, True))

    def op_ooidentityhash(self, result, arg):
        yield "(setf %s (sxhash %s))" % (clrepr(result, True),
                                         clrepr(arg, True))

    def op_oononnull(self, result, arg):
        yield "(setf %s (not (null %s)))" % (clrepr(result, True),
                                             clrepr(arg, True))


class ListImpl:

    def __init__(self, receiver):
        self.obj = clrepr(receiver)

    def ll_length(self):
        return "(length %s)" % (self.obj,)

    def ll_getitem_fast(self, index):
        index = clrepr(index)
        return "(aref %s %s)" % (self.obj, index)

    def ll_setitem_fast(self, index, value):
        index = clrepr(index)
        value = clrepr(value)
        return "(setf (aref %s %s) %s)" % (self.obj, index, value)

    def _ll_resize(self, size):
        size = clrepr(size)
        return "(adjust-array %s %s)" % (self.obj, size)


class GenCL:

    def __init__(self, context, funobj):
        self.context = context
        self.entry_point = funobj
        self.entry_name = clrepr(funobj.func_name, symbol=True)
        self.pendinggraphs = [funobj]
        self.declarations = InsertionOrderedDict()
        self.constcount = 0
        self.structcount = 0

    def is_exception_instance(self, INST):
        exceptiondata = self.context.rtyper.exceptiondata
        return exceptiondata.is_exception_instance(INST)

    def check_declaration(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, Instance):
                return self.declare_constant_instance(arg)
        return clrepr(arg)

    def declare_struct(self, cls):
        # cls is Record
        if cls in self.declarations:
            return self.declarations[cls][0]
        name = "struct" + str(self.structcount)
        field_declaration = cls._fields.keys()
        field_declaration = " ".join(field_declaration)
        struct_declaration = "(defstruct %s %s)" % (name, field_declaration)
        self.declarations[cls] = (name, struct_declaration)
        self.structcount += 1
        return name

    def declare_class(self, cls):
        # cls is Instance
        if cls in self.declarations:
            return self.declarations[cls][0]
        name = clrepr(cls._name, symbol=True)
        field_declaration = []
        for field in cls._fields:
            field = clrepr(field, True)
            field_declaration.append('('+field+' :accessor '+field+')')
        field_declaration = " ".join(field_declaration)
        if cls._superclass is ROOT:
            class_declaration = "(defclass %s () (%s))" % (name, field_declaration)
        else:
            self.declare_class(cls._superclass)
            supername = clrepr(cls._superclass._name, symbol=True)
            class_declaration = "(defclass %s (%s) (%s))" % (name, supername, field_declaration)
        self.declarations[cls] = (name, class_declaration)
        for method in cls._methods:
            methodobj = cls._methods[method]
            methodobj._method_name = method
            self.pendinggraphs.append(methodobj)
        return name

    def declare_exception(self, cls):
        # cls is Instance
        assert self.is_exception_instance(cls)
        if cls in self.declarations:
            return self.declarations[cls][0]
        name = clrepr(cls._name, symbol=True)
        if cls._superclass is OBJECT:
            exception_declaration = "(define-condition %s () ((meta :accessor meta)))" % (name)
        else:
            supername = self.declare_exception(cls._superclass)
            exception_declaration = "(define-condition %s (%s) ())" % (name, supername)
        self.declarations[cls] = (name, exception_declaration)
        return name

    def declare_constant_instance(self, const):
        # const.concretetype is Instance
        if const in self.declarations:
            return self.declarations[const][0]
        if const.value is const.concretetype._null:
            return "nil"
        name = "const" + str(self.constcount)
        INST = dynamicType(const.value)
        self.declare_class(INST)
        inst = oodowncast(INST, const.value)
        cls = clrepr(INST)
        const_declaration = []
        const_declaration.append("(setf %s (make-instance %s))" % (clrepr(name, True),
                                                                   clrepr(cls, True)))
        fields = INST._allfields()
        for fieldname in fields:
            fieldvalue = getattr(inst, fieldname)
            if isinstance(fieldvalue, _class):
                self.declare_class(fieldvalue._INSTANCE)
            fieldvaluerepr = clrepr(getattr(inst, fieldname))
            ### XXX
            const_declaration.append("(setf (slot-value %s '%s) %s)" % (clrepr(name, True),
                                                                        clrepr(fieldname, True),
                                                                        clrepr(fieldvaluerepr, True)))
        const_declaration = "\n".join(const_declaration)
        self.declarations[const] = (name, const_declaration)
        self.constcount += 1
        return name

    def emitfile(self):
        name = self.entry_name
        path = udir.join("%s.lisp" % (name,))
        code = self.emitcode()
        path.write(code)
        return str(path)

    def emitcode(self):
        lines = list(self.emit())
        declarations = "\n".join([d[1] for d in self.declarations.values()])
        code = "\n".join(lines)
        if declarations:
            return declarations + "\n" + code + "\n"
        else:
            return code + "\n"

    def emit(self):
        while self.pendinggraphs:
            obj = self.pendinggraphs.pop()
            if isinstance(obj, types.FunctionType):
                graph = graphof(self.context, obj)
                for line in self.emit_defun(graph):
                    yield line
            elif isinstance(obj, _static_meth):
                graph = obj.graph
                for line in self.emit_defun(graph):
                    yield line
            elif isinstance(obj, _meth):
                graph = obj.graph
                name = obj._method_name # XXX
                for line in self.emit_defmethod(graph, name):
                    yield line

    def emit_defun(self, fun):
        yield "(defun " + clrepr(fun.name, symbol=True)
        arglist = fun.getargs()
        args = " ".join(map(lambda item: clrepr(item, True), arglist))
        yield "(%s)" % (args,)
        for line in self.emit_body(fun, arglist):
            yield line

    def emit_defmethod(self, fun, name):
        yield "(defmethod %s" % (clrepr(name, symbol=True))
        arglist = fun.getargs()
        selfvar = clrepr(arglist[0], True)
        clsname = clrepr(arglist[0].concretetype._name, symbol=True)
        args = " ".join(map(lambda item: clrepr(item, True), arglist[1:]))
        if args:
            yield "((%s %s) %s)" % (clrepr(selfvar, True),
                                    clrepr(clsname, True),
                                    clrepr(args, True))
        else:
            yield "((%s %s))" % (clrepr(selfvar, True),
                                 clrepr(clsname, True))
        for line in self.emit_body(fun, arglist):
            yield line

    def emit_body(self, fun, arglist):
        yield "(prog"
        blocklist = list(fun.iterblocks())
        vardict = {}
        self.blockref = {}
        for block in blocklist:
            tag = len(self.blockref)
            self.blockref[block] = tag
            for var in block.getvariables():
                # In the future, we could assign type information here
                vardict[var] = None
        varnames = []
        for var in vardict:
            varname = clrepr(var)
            if var in arglist:
                varnames.append("(%s %s)" % (clrepr(varname, True),
                                             clrepr(varname, True)))
            else:
                varnames.append(clrepr(varname, True))
        varnames = " ".join(varnames)
        yield "(%s)" % (varnames,)
        for block in blocklist:
            for line in self.emit_block(block):
                yield line
        yield "))"

    def emit_block(self, block):
        self.cur_block = block
        tag = self.blockref[block]
        yield "tag" + clrepr(str(tag), True)
        if block.exitswitch is c_last_exception:
            yield "(handler-case (progn"
        for op in block.operations:
            emit_op = Op(self, op)
            for line in emit_op:
                yield line
        exits = block.exits
        if len(exits) == 1:
            for line in self.emit_link(exits[0]):
                yield line
        elif len(exits) > 1:
            # only works in the current special case
            if (len(exits) == 2 and
                exits[0].exitcase == False and
                exits[1].exitcase == True):
                yield "(if " + clrepr(block.exitswitch, True)
                yield "(progn"
                for line in self.emit_link(exits[1]):
                    yield line
                yield ") ; else"
                yield "(progn"
                for line in self.emit_link(exits[0]):
                    yield line
                yield "))"
            elif block.exitswitch is c_last_exception:
                body = None
                exceptions = {}
                for exit in exits:
                    if exit.exitcase is None:
                        body = exit
                    else:
                        cls = exit.llexitcase.class_._INSTANCE
                        exception = self.declare_exception(cls)
                        exceptions[exception] = exit
                for line in self.emit_link(body):
                    yield line
                yield ")" # closes the progn for the handler-case
                for exception in exceptions:
                    yield "(%s ()" % (exception,)
                    for line in self.emit_link(exceptions[exception]):
                        yield line
                    yield ")"
            else:
                # this is for the more general case.  The previous special case
                # shouldn't be needed but in Python 2.2 we can't tell apart
                # 0 vs nil  and  1 vs t  :-(
                for exit in exits[:-1]:
                    yield "(if (equalp " + clrepr(block.exitswitch, True)
                    yield clrepr(exit.exitcase, True) + ')'
                    yield "(progn"
                    for line in self.emit_link(exit):
                        yield line
                    yield ")"
                yield "(progn ; else should be %s" % clrepr(exits[-1].exitcase, True)
                for line in self.emit_link(exits[-1]):
                    yield line
                yield ")" * len(exits)
        elif len(block.inputargs) == 2:
            exc_value = clrepr(block.inputargs[1], True)
            yield "(error %s)" % (exc_value,)
        else:
            retval = clrepr(block.inputargs[0])
            yield "(return %s)" % clrepr(retval, True)
        if block.exitswitch is c_last_exception:
            yield ")"

    def format_jump(self, block):
        tag = self.blockref[block]
        return "(go tag" + clrepr(str(tag), True) + ")"

    def emit_link(self, link):
        source = map(self.check_declaration, link.args)
        target = map(clrepr, link.target.inputargs)
        couples = [ "%s %s" % (clrepr(t, True), clrepr(s, True)) for (s, t) in zip(source, target)]
        couples = " ".join(couples)
        yield "(setf %s)" % (couples,)
        yield self.format_jump(link.target)
