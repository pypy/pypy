import datetime
from pypy.objspace.flow.model import Constant, Variable, c_last_exception
from pypy.translator.squeak.opformatter import OpFormatter
from pypy.translator.squeak.codeformatter import CodeFormatter, Message
from pypy.translator.squeak.codeformatter import Field, Assignment, CustomVariable
from pypy.rpython.ootypesystem.ootype import Instance, Class, ROOT, _view

class CodeNode:

    def __hash__(self):
        return hash(self.hash_key)
    
    def __eq__(self, other):
        return isinstance(other, CodeNode) \
                and self.hash_key == other.hash_key
    
    def render_fileout_header(self, class_name, category):
        return "!%s methodsFor: '%s' stamp: 'pypy %s'!" % (
                class_name, category,
                datetime.datetime.now().strftime("%m/%d/%Y %H:%M"))

class ClassNode(CodeNode):

    def __init__(self, gen, INSTANCE, class_vars=None, host_base=None):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.class_vars = [] # XXX should probably go away
        if class_vars is not None:
            self.class_vars = class_vars
        self.host_base = host_base
        self.hash_key = INSTANCE

    def dependencies(self):
        deps = []
        if self.INSTANCE._superclass is not None \
                and self.host_base is None: # not root
            deps.append(ClassNode(self.gen, self.INSTANCE._superclass))
        return deps

    def render(self):
        codef = CodeFormatter(self.gen)
        if self.host_base is None:
            superclass = codef.format_Instance(self.INSTANCE._superclass) 
        else:
            superclass = self.host_base
        yield "%s subclass: #%s" % \
                (superclass, codef.format_Instance(self.INSTANCE))
        fields = [self.gen.unique_field_name(self.INSTANCE, f) for f in
            self.INSTANCE._fields.iterkeys()]
        yield "    instanceVariableNames: '%s'" % ' '.join(fields)
        yield "    classVariableNames: '%s'" % ' '.join(self.class_vars)
        yield "    poolDictionaries: ''"
        yield "    category: 'PyPy-Test'!"

class LoopFinder:

    def __init__(self, startblock):
        self.loops = {}
        self.parents = {startblock: startblock}
        self.temps = {}
        self.seen = []
        self.visit_Block(startblock)
   
    def visit_Block(self, block, switches=[]):
        #self.temps.has_key()
        self.seen.append(block)
        if block.exitswitch:
            switches.append(block)
            self.parents[block] = block
        for link in block.exits:
            self.visit_Link(link, switches) 

    def visit_Link(self, link, switches):
        if link.target in switches:
            self.loops[link.target] = True
        if not link.target in self.seen:
            self.parents[link.target] = self.parents[link.prevblock]
            self.visit_Block(link.target, switches)

class CallableNode(CodeNode):

    OPERATION_ERROR = Instance("OperationError", ROOT,
            fields={"type": Class, "value": ROOT})

    def dependencies(self):
        return [ClassNode(self.gen, self.OPERATION_ERROR, host_base="Exception")]

    def render_body(self, startblock):
        self.codef = CodeFormatter(self.gen)
        self.loops = LoopFinder(startblock).loops
        args = self.arguments(startblock)
        message = Message(self.unique_name).with_args(args)
        yield self.codef.format(message)
 
        # XXX should declare local variables here
        for line in self.render_block(startblock):
            yield "    %s" % line
        yield '! !'

    def render_return(self, args):
        if len(args) == 2:
            # exception
            yield self.render_exception(args[0], args[1])
        else:
            # regular return block
            retval = self.codef.format(args[0])
            yield "^%s" % retval

    def render_exception(self, exception_class, exception_value):
        exc_cls = self.codef.format(exception_class)
        exc_val = self.codef.format(exception_value)
        return "((%s new) type: %s; value: %s) signal." \
                % (self.codef.format_Instance(self.OPERATION_ERROR),
                        exc_cls, exc_val)

    def render_link(self, link):
        block = link.target
        if link.args:
            for i in range(len(link.args)):
                yield '%s := %s.' % \
                        (self.codef.format(block.inputargs[i]),
                                self.codef.format(link.args[i]))
        for line in self.render_block(block):
            yield line

    def render_block(self, block):
        if self.loops.has_key(block):
            if not self.loops[block]:
                yield '"skip1"'
                return
            yield "["
        if block.exitswitch is c_last_exception:
            yield "["
        formatter = OpFormatter(self.gen, self)
        for op in block.operations:
            yield "%s." % formatter.format(op)
        if len(block.exits) == 0:
            for line in self.render_return(block.inputargs):
                yield line
            return
        elif block.exitswitch is None:
            # single-exit block
            assert len(block.exits) == 1
            for line in self.render_link(block.exits[0]):
                yield line
        elif block.exitswitch is c_last_exception:
            # exception branching
            # wuah. ugly!
            codef = formatter.codef
            exc_var = self.gen.unique_name(("var", "exception"), "exception")
            yield "] on: %s do: [:%s |" \
                    % (codef.format(self.OPERATION_ERROR), exc_var)
            exc_exits = []
            non_exc_exit = None
            for exit in block.exits:
                if exit.exitcase is None:
                    non_exc_exit = exit
                else:
                    exc_exits.append(exit)
            for exit in exc_exits:
                yield "(%s type isKindOf: %s) ifTrue: [" \
                        % (exc_var, codef.format(exit.llexitcase))
                if exit.last_exception is not None:
                    yield "%s := %s type." \
                            % (codef.format(exit.last_exception), exc_var)
                if exit.last_exc_value is not None:
                    yield "%s := %s value." \
                            % (codef.format(exit.last_exc_value), exc_var)
                for line in self.render_link(exit):
                    yield line
                yield "] ifFalse: ["
            for exit in exc_exits:
                yield "]"
            yield "]."
            for line in self.render_link(non_exc_exit):
                yield line
        else:
            #exitswitch
            if self.loops.has_key(block):
                if self.loops[block]:
                    self.loops[block] = False
                    yield "%s] whileTrue: [" % self.codef.format(block.exitswitch)
                    for line in self.render_link(block.exits[True]):
                        yield "    %s" % line
                    yield "]."
                    for line in self.render_link(block.exits[False]):
                        yield "%s" % line
            else:
                yield "%s ifTrue: [" % self.codef.format(block.exitswitch)
                for line in self.render_link(block.exits[True]):
                    yield "    %s" % line
                yield "] ifFalse: [" 
                for line in self.render_link(block.exits[False]):
                    yield "    %s" % line
                yield "]"

class MethodNode(CallableNode):

    def __init__(self, gen, INSTANCE, method_name):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.name = method_name
        self.unique_name = gen.unique_method_name(
                INSTANCE, method_name, schedule=False)
        self.self = None # Will be set upon rendering
        self.hash_key = (INSTANCE, method_name)

    def dependencies(self):
        return CallableNode.dependencies(self) \
                + [ClassNode(self.gen, self.INSTANCE)]

    def arguments(self, startblock):
        # Omit the explicit self
        return startblock.inputargs[1:]
    
    def render(self):
        codef = CodeFormatter(self.gen)
        yield self.render_fileout_header(
                codef.format(self.INSTANCE), "methods")
        graph = self.INSTANCE._methods[self.name].graph
        self.self = graph.startblock.inputargs[0]
        for line in self.render_body(graph.startblock):
            yield line

class FunctionNode(CallableNode):
    
    FUNCTIONS = Instance("Functions", ROOT)

    def __init__(self, gen, graph):
        self.gen = gen
        self.graph = graph
        self.unique_name = gen.unique_func_name(graph, schedule=False)
        self.self = None
        self._class_name = gen.unique_class_name(self.FUNCTIONS)
        self.hash_key = graph

    def dependencies(self):
        return CallableNode.dependencies(self) \
                + [ClassNode(self.gen, self.FUNCTIONS)]

    def arguments(self, startblock):
        return startblock.inputargs
    
    def render(self):
        yield self.render_fileout_header(
                "%s class" % self._class_name, "functions")
        for line in self.render_body(self.graph.startblock):
            yield line

class AccessorNode(CodeNode):

    def __init__(self, gen, INSTANCE, field_name):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.field_name = field_name
        self.unique_name = gen.unique_field_name(
                INSTANCE, field_name, schedule=False)
        self.codef = CodeFormatter(gen)
        self.hash_key = (INSTANCE, field_name, self.__class__)

    def dependencies(self):
        return [ClassNode(self.gen, self.INSTANCE)]

class SetterNode(AccessorNode):

    def render(self):
        yield self.render_fileout_header(
                self.codef.format(self.INSTANCE), "accessors")
        arg_name = self.gen.unique_name((SetterNode, "arg"), "value")
        yield "%s: %s" % (self.unique_name, arg_name)
        yield "    %s := %s" % (self.unique_name, arg_name)
        yield "! !"

class GetterNode(AccessorNode):

    def render(self):
        yield self.render_fileout_header(
                self.codef.format(self.INSTANCE), "accessors")
        yield self.unique_name
        yield "    ^%s" % self.unique_name
        yield "! !"

class HelperNode(CodeNode):
    
    HELPERS = Instance("Helpers", ROOT)

    def __init__(self, gen, message, code):
        self.gen = gen
        self.message = message
        self.code = code
        self._class_name = gen.unique_class_name(self.HELPERS)
        self.hash_key = ("helper", code)

    def apply(self, args):
        return self.message.send_to(self.HELPERS, args)
    
    def dependencies(self):
        return [ClassNode(self.gen, self.HELPERS)]

    def render(self):
        # XXX should not use explicit name "PyHelpers" here
        yield self.render_fileout_header(
                "%s class" % self._class_name, "helpers")
        for line in self.code.strip().split("\n"):
            yield line
        yield "! !"

class FieldInitializerNode(CodeNode):

    def __init__(self, gen, INSTANCE):
        self.gen = gen
        self.INSTANCE = INSTANCE
        self.hash_key = ("fieldinit", INSTANCE)

    def dependencies(self):
        return [ClassNode(self.gen, self.INSTANCE)]

    def render(self):
        codef = CodeFormatter(self.gen)
        yield self.render_fileout_header(
                codef.format(self.INSTANCE), "initializers")
        fields = self.INSTANCE._allfields()
        args = [CustomVariable("a%s" % i) for i in range(len(fields))]
        message = Message("fieldInit").with_args(args)
        yield codef.format(message)
        for field_name, arg in zip(fields.keys(), args):
            unique_field = self.gen.unique_field_name(self.INSTANCE, field_name)
            ass = Assignment(Field(unique_field), arg)
            yield "    %s." % codef.format(ass)
        yield "! !"

class SetupNode(CodeNode):

    CONSTANTS = Instance("Constants", ROOT)
    
    def __init__(self, gen, constants):
        self.gen = gen
        self.constants = constants
        self._class_name = gen.unique_class_name(self.CONSTANTS)
        self.hash_key = "setup"

    def dependencies(self):
        # Important: Field initializers for the *runtime* type
        return [FieldInitializerNode(self.gen, self._dynamic_type(c.value))
            for c in self.constants.iterkeys()] + \
            [ClassNode(self.gen, self.CONSTANTS, class_vars=["Constants"])]

    def _dynamic_type(self, instance):
        # XXX move this to ootype?
        if isinstance(instance, _view):
            return instance._inst._TYPE
        else:
            return instance._TYPE

    def render(self):
        codef = CodeFormatter(self.gen)
        # XXX use CodeFormatter throughout here
        yield self.render_fileout_header(
                "%s class" % self._class_name, "internals")
        message = Message("setupConstants")
        yield codef.format(message.with_args([]))
        yield "    Constants := Dictionary new."
        for const, const_id in self.constants.iteritems():
            INST = self._dynamic_type(const.value)
            inst = const.value._downcast(INST)
            field_names = INST._allfields().keys()
            field_values = [getattr(inst, f) for f in field_names]
            new = Message("new").send_to(INST, [])
            init_message = Message("fieldInit").send_to(new, field_values)
            yield "    Constants at: '%s' put: %s." \
                    % (const_id, codef.format(init_message))
        yield "! !"
        yield ""

        yield self.render_fileout_header(
                "%s class" % self._class_name, "internals")
        arg = CustomVariable("constId")
        get_message = Message("getConstant")
        yield codef.format(get_message.with_args([arg]))
        yield "    ^ Constants at: constId"
        yield "! !"

