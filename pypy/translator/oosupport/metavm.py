
"""
Varius microopcodes for different ootypesystem based backends

These microopcodes are used to translate from the ootype operations to
the operations of a particular backend.  For an example, see
cli/opcodes.py which maps from ootype opcodes to sets of metavm
instructions.

See the MicroInstruction class for discussion on the methods of a
micro-op.
"""

from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.bltregistry import ExternalType
from pypy.rpython.extfunc import ExtFuncEntry, is_external

class Generator(object):
    
    def add_comment(self, text):
        """
        Called w/in a function w/ a text string that could be
        usefully added to the output.
        """
        pass

    def add_section(self, text):
        """
        Prints a distinguished comment
        """
        self.add_comment("_" * 70)
        self.add_comment(text)

    def pop(self, TYPE):
        """ Pops a value off the top of the stack, which is of the
        given TYPE.

        Stack: val, ... -> ..."""
        raise NotImplementedError

    def dup(self, TYPE):
        """ Duplicates the top of the stack, which is of the given TYPE.

        Stack: val, ... -> val, val, ..."""
        raise NotImplementedError

    def emit(self, instr, *args):
        """
        Invoked by InstructionList.render() when we encounter a
        non-MicroInstruction in the list of instructions.  This is
        typically used to encode small single operands as strings.
        """
        pass

    def load(self, v):
        """
        Loads an item 'v' onto the stack
        
        Stack: ... -> v, ...
        """
        pass

    def store(self, v):
        """
        Stores an item from the stack into 'v'
        
        Stack: value, ... -> ...
        """
        pass

    def set_field(self, CONCRETETYPE, fieldname):
        """
        Stores a value into a field.
        
        'CONCRETETYPE' should be the type of the class that has the field
        'fieldname' is a string with the name of the field
        
        Stack: value, item, ... -> ...
        """
        raise NotImplementedError

    def get_field(self, CONCRETETYPE, fieldname):
        """
        Gets a value from a specified field.

        'CONCRETETYPE' should be the type of the class that has the field
        'fieldname' is the name of the field

        Stack: item, ... -> ...
        """
        raise NotImplementedError

    def downcast(self, TYPE):
        """
        Casts the object on the top of the stack to be of the specified
        ootype.  Assumed to raise an exception on failure.
        
        Stack: obj, ... -> obj, ...
        """
        raise NotImplementedError

    def getclassobject(self, OOINSTANCE):
        """
        Gets the class object for the OOINSTANCE.  The type of the class
        object will depend on the backend, of course; for example in JVM
        it is java.lang.Class.
        """
        raise NotImplementedError

    def instantiate(self):
        """
        Instantiates an instance of the Class object that is on top of
        the stack.  Class objects refers to an object representing a
        class.  Used to implement RuntimeNew.

        Stack: class_obj, ... -> instance_obj, ...
        """
        raise NotImplementedError

    def instanceof(self, TYPE):
        """
        Determines whether the object on the top of the stack is an
        instance of TYPE (an ootype).
        
        Stack: obj, ... -> boolean, ...
        """
        pass

    def branch_unconditionally(self, target_label):
        """ Branches to target_label unconditionally """
        raise NotImplementedError

    def branch_conditionally(self, iftrue, target_label):
        """ Branches to target_label depending on the value on the top of
        the stack.  If iftrue is True, then the branch occurs if the value
        on top of the stack is true; if iftrue is false, then the branch
        occurs if the value on the top of the stack is false

        Stack: cond, ... -> ... """
        raise NotImplementedError

    def branch_if_equal(self, target_label):
        """
        Pops two values from the stack and branches to target_label if
        they are equal.

        Stack: obj1, obj2, ... -> ...
        """
        raise NotImplementedError

    def call_graph(self, graph):
        """ Invokes the function corresponding to the given graph.  The
        arguments to the graph have already been pushed in order
        (i.e., first argument pushed first, etc).  Pushes the return
        value.

        Stack: argN...arg2, arg1, arg0, ... -> ret, ... """
        raise NotImplementedError

    def prepare_generic_argument(self, ITEMTYPE):
        """
        Invoked after a generic argument has been pushed onto the stack.
        May not need to do anything, but some backends, *cough*Java*cough*,
        require boxing etc.
        """
        return # by default do nothing

    def call_method(self, OOCLASS, method_name):
        """ Invokes the given method on the object on the stack.  The
        this ptr and all arguments have already been pushed.

        Stack: argN, arg2, arg1, this, ... -> ret, ... """
        raise NotImplementedError

    def prepare_call_primitive(self, op, module, name):
        """ see call_primitive: by default does nothing """
        pass
        
    def call_primitive(self, op, module, name):
        """ Like call_graph, but it has been suggested that the method be
        rendered as a primitive.  The full sequence for invoking a primitive:

          self.prepare_call_primitive(op, module, name)
          for each arg: self.load(arg)
          self.call_primitive(op, module, name)

        Stack: argN...arg2, arg1, arg0, ... -> ret, ... """
        raise NotImplementedError

    def prepare_call_oostring(self, OOTYPE):
        " see call_oostring "
        pass

    def call_oostring(self, OOTYPE):
        """ Invoked for the oostring opcode with both operands
        (object, int base) already pushed onto the stack.
        prepare_call_oostring() is invoked before the operands are
        pushed."""
        raise NotImplementedError

    def prepare_call_oounicode(self, OOTYPE):
        " see call_oounicode "
        pass

    def call_oounicode(self, OOTYPE):
        """ Invoked for the oounicode opcode with the operand already
        pushed onto the stack.  prepare_call_oounicode() is invoked
        before the operand is pushed. """
        raise NotImplementedError

    def new(self, TYPE):
        """ Creates a new object of the given type.

        Stack: ... -> newobj, ... """
        raise NotImplementedError

    def oonewarray(self, TYPE, length):
        """ Creates a new array of the given type with the given length.

        Stack: ... -> newobj, ... """
        raise NotImplementedError


    def push_null(self, TYPE):
        """ Push a NULL value onto the stack (the NULL value represents
        a pointer to an instance of OOType TYPE, if it matters to you). """
        raise NotImplementedError

    def push_primitive_constant(self, TYPE, value):
        """ Push an instance of TYPE onto the stack with the given
        value.  TYPE will be one of the types enumerated in
        oosupport.constant.PRIMITIVE_TYPES.  value will be its
        corresponding ootype implementation. """
        raise NotImplementedError

    def get_instrution_count(self):
        """
        Return the number of opcodes in the current function, or -1
        if the backend doesn't care about it. Default is -1
        """
        return -1

class InstructionList(list):
    def render(self, generator, op):
        for instr in self:
            if isinstance(instr, MicroInstruction):
                instr.render(generator, op)
            else:
                generator.emit(instr)
    
    def __call__(self, *args):
        return self.render(*args)


class MicroInstruction(object):
    def render(self, generator, op):
        """
        Generic method which emits code to perform this microinstruction.
        
        'generator' -> the class which generates actual code emitted
        'op' -> the instruction from the FlowIR
        """
        pass

    def __str__(self):
        return self.__class__.__name__
    
    def __call__(self, *args):
        return self.render(*args)

class _DoNothing(MicroInstruction):
    def render(self, generator, op):
        pass
        
class PushArg(MicroInstruction):
    """ Pushes a given operand onto the stack. """
    def __init__(self, n):
        self.n = n

    def render(self, generator, op):
        generator.load(op.args[self.n])

class _PushAllArgs(MicroInstruction):
    """ Pushes all arguments of the instruction onto the stack in order. """
    def __init__(self, slice=None):
        """ Eventually slice args
        """
        self.slice = slice
    
    def render(self, generator, op):
        if self.slice is not None:
            args = op.args[self.slice]
        else:
            args = op.args
        for arg in args:
            generator.load(arg)

class PushPrimitive(MicroInstruction):
    def __init__(self, TYPE, value):
        self.TYPE = TYPE
        self.value = value

    def render(self, generator, op):
        generator.push_primitive_constant(self.TYPE, self.value)
        
class _StoreResult(MicroInstruction):
    def render(self, generator, op):
        generator.store(op.result)

class _SetField(MicroInstruction):
    def render(self, generator, op):
        this, field, value = op.args
##        if field.value == 'meta':
##            return # TODO
        
        if value.concretetype is ootype.Void:
            return
        generator.load(this)
        generator.load(value)
        generator.set_field(this.concretetype, field.value)

class _GetField(MicroInstruction):
    def render(self, generator, op):
        # OOType produces void values on occassion that can safely be ignored
        if op.result.concretetype is ootype.Void:
            return
        this, field = op.args
        generator.load(this)
        generator.get_field(this.concretetype, field.value)

class _DownCast(MicroInstruction):
    """ Push the argument op.args[0] and cast it to the desired type, leaving
    result on top of the stack. """
    def render(self, generator, op):
        RESULTTYPE = op.result.concretetype
        generator.load(op.args[0])
        generator.downcast(RESULTTYPE)

class _InstanceOf(MicroInstruction):
    """ Push the argument op.args[0] and cast it to the desired type, leaving
    result on top of the stack. """
    def render(self, generator, op):
        RESULTTYPE = op.result.concretetype
        generator.load(op.args[0])
        generator.instanceof(RESULTTYPE)

# There are three distinct possibilities where we need to map call differently:
# 1. Object is marked with rpython_hints as a builtin, so every attribut access
#    and function call goes as builtin
# 2. Function called is a builtin, so it might be mapped to attribute access, builtin function call
#    or even method call
# 3. Object on which method is called is primitive object and method is mapped to some
#    method/function/attribute access
class _GeneralDispatcher(MicroInstruction):
    def __init__(self, builtins, class_map):
        self.builtins = builtins
        self.class_map = class_map
    
    def render(self, generator, op):
        raise NotImplementedError("pure virtual class")
    
    def check_builtin(self, this):
        if not isinstance(this, ootype.Instance):
            return False
        return this._hints.get('_suggested_external')
    
    def check_external(self, this):
        if isinstance(this, ExternalType):
            return True
        return False

class _MethodDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        method = op.args[0].value
        this = op.args[1].concretetype
        if self.check_external(this):
            return self.class_map['CallExternalObject'].render(generator, op)
        if self.check_builtin(this):
            return self.class_map['CallBuiltinObject'].render(generator, op)
        try:
            self.builtins.builtin_obj_map[this.__class__][method](generator, op)
        except KeyError:
            return self.class_map['CallMethod'].render(generator, op)

class _CallDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        func = op.args[0]
        # XXX we need to sort out stuff here at some point
        if is_external(func):
            func_name = func.value._name.split("__")[0]
            try:
                return self.builtins.builtin_map[func_name](generator, op)
            except KeyError:
                return self.class_map['CallBuiltin'](func_name)(generator, op)
        return self.class_map['Call'].render(generator, op)
    
class _GetFieldDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        if self.check_builtin(op.args[0].concretetype):
            return self.class_map['GetBuiltinField'].render(generator, op)
        else:
            return self.class_map['GetField'].render(generator, op)
    
class _SetFieldDispatcher(_GeneralDispatcher):
    def render(self, generator, op):
        if self.check_external(op.args[0].concretetype):
            return self.class_map['SetExternalField'].render(generator, op)
        elif self.check_builtin(op.args[0].concretetype):
            return self.class_map['SetBuiltinField'].render(generator, op)
        else:
            return self.class_map['SetField'].render(generator, op)

class _New(MicroInstruction):
    def render(self, generator, op):
        try:
            op.args[0].value._hints['_suggested_external']
            generator.ilasm.new(op.args[0].value._name.split('.')[-1])
        except (KeyError, AttributeError):
            if op.args[0].value is ootype.Void:
                return
            generator.new(op.args[0].value)


class _OONewArray(MicroInstruction):
    def render(self, generator, op):
        if op.args[0].value is ootype.Void:
            return
        generator.oonewarray(op.args[0].value, op.args[1])


class BranchUnconditionally(MicroInstruction):
    def __init__(self, label):
        self.label = label
    def render(self, generator, op):
        generator.branch_unconditionally(self.label)

class BranchIfTrue(MicroInstruction):
    def __init__(self, label):
        self.label = label
    def render(self, generator, op):
        generator.branch_conditionally(True, self.label)

class BranchIfFalse(MicroInstruction):
    def __init__(self, label):
        self.label = label
    def render(self, generator, op):
        generator.branch_conditionally(False, self.label)


class _Call(MicroInstruction):

    def _get_primitive_name(self, callee):
        try:
            graph = callee.graph
        except AttributeError:
            return callee._name.rsplit('.', 1)

    def render(self, generator, op):
        callee = op.args[0].value
        is_primitive = self._get_primitive_name(callee)

        if is_primitive:
            module, name = is_primitive
            generator.prepare_call_primitive(op, module, name)

        for arg in op.args[1:]:
            generator.load(arg)

        if is_primitive:
            generator.call_primitive(op, module, name)
        else:
            generator.call_graph(callee.graph)

            
class _CallMethod(MicroInstruction):
    def render(self, generator, op):
        method = op.args[0] # a FlowConstant string...
        this = op.args[1]
        for arg in op.args[1:]:
            generator.load(arg)
        generator.call_method(this.concretetype, method.value)

class _RuntimeNew(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        generator.instantiate()
        generator.downcast(op.result.concretetype)

class _OOString(MicroInstruction):
    def render(self, generator, op):
        ARGTYPE = op.args[0].concretetype
        generator.prepare_call_oostring(ARGTYPE)
        generator.load(op.args[0])
        generator.load(op.args[1])
        generator.call_oostring(ARGTYPE)

class _OOUnicode(MicroInstruction):
    def render(self, generator, op):
        v_base = op.args[1]
        assert v_base.value == -1, "The second argument of oounicode must be -1"

        ARGTYPE = op.args[0].concretetype
        generator.prepare_call_oounicode(ARGTYPE)
        generator.load(op.args[0])
        generator.call_oounicode(ARGTYPE)

class _CastTo(MicroInstruction):
    def render(self, generator, op):
        generator.load(op.args[0])
        INSTANCE = op.args[1].value
        class_name = generator.db.pending_class(INSTANCE)
        generator.isinstance(class_name)

New = _New()
OONewArray = _OONewArray()

PushAllArgs = _PushAllArgs()
StoreResult = _StoreResult()
SetField = _SetField()
GetField = _GetField()
DownCast = _DownCast()
DoNothing = _DoNothing()
Call = _Call()
CallMethod = _CallMethod()
RuntimeNew = _RuntimeNew()
OOString = _OOString()
OOUnicode = _OOUnicode()
CastTo = _CastTo()

