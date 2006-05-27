import types

from pypy.tool.udir import udir
from pypy.objspace.flow.model import Constant, c_last_exception, FunctionGraph
from pypy.translator.translator import graphof
from pypy.rpython.ootypesystem.ootype import dynamicType, oodowncast, null, Record, Instance, _class, _static_meth, _meth, ROOT
from pypy.rpython.ootypesystem.rclass import OBJECT
from pypy.translator.cl.clrepr import clrepr
from pypy.translator.cl.opformatter import OpFormatter

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
            if isinstance(arg.concretetype, (Record, Instance)):
                if arg.value is null(arg.concretetype):
                    return "nil"
            if isinstance(arg.concretetype, Instance):
                return self.declare_constant_instance(arg)
        return clrepr(arg)

    def declare_any(self, cls):
        if isinstance(cls, Record):
            return self.declare_struct(cls)
        if isinstance(cls, Instance):
            if self.is_exception_instance(cls):
                return self.declare_exception(cls)
            else:
                return self.declare_class(cls)
        raise NotImplementedError("cannot declare %s" % (cls,))

    def declare_struct(self, cls):
        assert isinstance(cls, Record)
        if cls in self.declarations:
            return self.declarations[cls][0]
        name = "struct" + str(self.structcount)
        field_declaration = cls._fields.keys()
        field_declaration = " ".join(field_declaration)
        struct_declaration = "(defstruct %s %s)" % (name, field_declaration)
        self.declarations[cls] = (name, struct_declaration)
        self.structcount += 1
        return name

    def declare_dict_iter(self):
        name = 'pypy-dict-iter'
        if name in self.declarations:
            return self.declarations[name][0]
        definition = """\
(defun %s (hash)
  (let ((current-index -1)
        (keys (loop for keys being the hash-keys in hash collect keys)))
      (list (lambda ()
              (let ((more (<= (incf current-index) (1- (length keys)))))
                (if more
                  (let* ((key (nth current-index keys))
                         (val (gethash key hash)))
                    (values more key val))
                  (values nil nil nil))))
            (lambda ()
              (nth current-index keys))
            (lambda ()
              (gethash (nth current-index keys) hash)))))""" % (name)
        self.declarations[name] = (name,  definition)
        return name

    def declare_class(self, cls):
        assert isinstance(cls, Instance)
        assert not self.is_exception_instance(cls)
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
        assert isinstance(cls, Instance)
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
        name = "+const" + str(self.constcount) + "+"
        INST = dynamicType(const.value)
        self.declare_class(INST)
        inst = oodowncast(INST, const.value)
        cls = clrepr(INST)
        const_declaration = []
        const_declaration.append("(defvar %s nil)" % clrepr(name, True))
        const_declaration.append("(setf %s (make-instance %s))" % (clrepr(name, True),
                                                                   clrepr(cls, True)))
        fields = INST._allfields()
        for fieldname in fields:
            fieldvalue = getattr(inst, fieldname)
            if isinstance(fieldvalue, _class):
                self.declare_any(fieldvalue._INSTANCE)
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
            elif isinstance(obj, FunctionGraph):
                graph = obj
                for line in self.emit_defun(graph):
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
        tag = self.blockref[block]
        yield "tag" + clrepr(str(tag), True)
        handle_exc = block.exitswitch == c_last_exception
        if handle_exc:
            yield "(handler-case (progn"
        for op in block.operations:
            emit_op = OpFormatter(self, op)
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
        if handle_exc:
            yield ")"

    def format_jump(self, block):
        tag = self.blockref[block]
        return "(go tag" + clrepr(str(tag), True) + ")"

    def emit_link(self, link):
        source = map(self.check_declaration, link.args)
        target = map(clrepr, link.target.inputargs)
        couples = ["%s %s" % (t, s) for (s, t) in zip(source, target)]
        if couples:
            couples = " ".join(couples)
            yield "(setf %s)" % (couples,)
        yield self.format_jump(link.target)
