from pypy.translator.cli.cts import CTS, PYPY_LIST_OF_VOID
from pypy.translator.cli.function import Function
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.record import Record
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype
from pypy.translator.cli.opcodes import opcodes

try:
    set
except NameError:
    from sets import Set as set

CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASS = 'Constants'

class LowLevelDatabase(object):
    def __init__(self, type_system_class = CTS, opcode_dict = opcodes, function_class = Function):
        self._pending_nodes = set()
        self.opcode_dict = opcode_dict
        self._rendered_nodes = set()
        self.function_class = function_class
        self.type_system_class = type_system_class
        self.cts = type_system_class(self)
        self.classes = {} # classdef --> class_name
        self.functions = {} # graph --> function_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> AbstractConst
        self.pending_consts = {} # value --> AbstractConst
        self.delegates = {} # StaticMethod --> type_name
        self.const_names = set()
        self.name_count = 0

    def next_count(self):
        self.name_count += 1
        return self.name_count

    def pending_function(self, graph):
        self.pending_node(self.function_class(self, graph))

    def pending_class(self, classdef):
        self.pending_node(Class(self, classdef))

    def pending_record(self, record):
        r = Record(self, record)
        self.pending_node(r)
        return r.get_name()

    def pending_node(self, node):
        if node in self._pending_nodes or node in self._rendered_nodes:
            return
        self._pending_nodes.add(node)

    def record_function(self, graph, name):
        self.functions[graph] = name

    def record_class(self, classdef, name):
        self.classes[classdef] = name

    def graph_name(self, graph):
        # XXX: graph name are not guaranteed to be unique
        return self.functions.get(graph, None)

    def class_name(self, classdef):
        return self.classes.get(classdef, None)

    def record_const(self, value):
        if value in self.consts:
            const = self.consts[value]
        elif value in self.pending_consts:
            const = self.pending_consts[value]
        else:
            const = AbstractConst.make(self, value, self.next_count())
            self.pending_consts[value] = const

        return '%s.%s::%s' % (CONST_NAMESPACE, CONST_CLASS, const.name)

    def record_delegate_type(self, TYPE):
        try:
            return self.delegates[TYPE]
        except KeyError:
            name = 'StaticMethod__%d' % len(self.delegates)
            # record we know about result and argument types
            self.cts.lltype_to_cts(TYPE.RESULT)
            for ARG in TYPE.ARGS:
                self.cts.lltype_to_cts(ARG)
            self.delegates[TYPE] = name
            return name

    def gen_delegate_types(self, ilasm):
        for TYPE, name in self.delegates.iteritems():
            ilasm.begin_class(name, '[mscorlib]System.MulticastDelegate')
            ilasm.begin_function('.ctor',
                                 [('object', "'object'"), ('native int', "'method'")],
                                 'void',
                                 False,
                                 'hidebysig', 'specialname', 'rtspecialname', 'instance', 'default',
                                 runtime=True)
            ilasm.end_function()

            resulttype = self.cts.lltype_to_cts(TYPE.RESULT)
            arglist = [(self.cts.lltype_to_cts(ARG), '') for ARG in TYPE.ARGS]
            ilasm.begin_function('Invoke', arglist, resulttype, False,
                                 'virtual', 'hidebysig', 'instance', 'default',
                                 runtime=True)
            ilasm.end_function()
            ilasm.end_class()
            
    
    def gen_constants(self, ilasm):
        ilasm.begin_namespace(CONST_NAMESPACE)
        ilasm.begin_class(CONST_CLASS)

        # initialize fields

        # This strange machinery it's necessary because it could be
        # happen that new constants are registered during rendering of
        # constants. So we split initialization of constants in a
        # number of 'steps' that are executed in reverse order as they
        # are rendered. The first step to be executed will be stepN,
        # the last step0.

        step = 0
        while self.pending_consts:
            pending_consts = self.pending_consts
            self.consts.update(pending_consts)
            self.pending_consts = {}

            # render field definitions
            for const in pending_consts.itervalues():
                ilasm.field(const.name, const.get_type(), static=True)

            ilasm.begin_function('step%d' % step, [], 'void', False, 'static')
            for const in pending_consts.itervalues():
                const.init(ilasm)
                type_ = const.get_type()
                ilasm.set_static_field (type_, CONST_NAMESPACE, CONST_CLASS, const.name)

            ilasm.ret()
            ilasm.end_function()
            step += 1

        # the constructor calls the steps in reverse order
        ilasm.begin_function('.cctor', [], 'void', False, 'static',
            'specialname', 'rtspecialname', 'default')

        last_step = step-1
        for step in xrange(last_step, -1, -1):
            func = '%s.%s::%s' % (CONST_NAMESPACE, CONST_CLASS, 'step%d' % step)
            ilasm.call('void %s()' % func)

        ilasm.ret()
        ilasm.end_function()

        ilasm.end_class()
        ilasm.end_namespace()


class AbstractConst(object):
    def make(db, value, count):
        if isinstance(value, ootype._view):
            static_type = value._TYPE
            value = value._inst
        else:
            static_type = None

        if isinstance(value, ootype._instance):
            return InstanceConst(db, value, static_type, count)
        elif isinstance(value, ootype._record):
            return RecordConst(db, value, count)
        elif isinstance(value, ootype._list):
            return ListConst(db, value, count)
        elif isinstance(value, ootype._string):
            return StringConst(db, value, count)
        elif isinstance(value, ootype._static_meth):
            return StaticMethodConst(db, value, count)
        elif isinstance(value, ootype._class):
            return ClassConst(db, value, count)
        else:
            assert False, 'Unknown constant: %s' % const
    make = staticmethod(make)

    def load(db, TYPE, value, ilasm):
        if TYPE is ootype.Void:
            pass
        elif TYPE is ootype.Bool:
            ilasm.opcode('ldc.i4', str(int(value)))
        elif TYPE is ootype.Char or TYPE is ootype.UniChar:
            ilasm.opcode('ldc.i4', ord(value))
        elif TYPE is ootype.Float:
            ilasm.opcode('ldc.r8', repr(value))
        elif TYPE in (ootype.Signed, ootype.Unsigned):
            ilasm.opcode('ldc.i4', str(value))
        elif TYPE in (lltype.SignedLongLong, lltype.UnsignedLongLong):
            ilasm.opcode('ldc.i8', str(value))
        else:
            cts = CTS(db)
            name = db.record_const(value)
            cts_type = cts.lltype_to_cts(TYPE)
            ilasm.opcode('ldsfld %s %s' % (cts_type, name))
    load = staticmethod(load)

    def get_name(self):
        pass

    def get_type(self):
        pass

    def init(self, ilasm):
        pass

class StringConst(AbstractConst):
    def __init__(self, db, string, count):
        self.db = db
        self.cts = CTS(db)
        self.string = string
        self.name = 'STRING_LITERAL__%d' % count

    def __hash__(self):
        return hash(self.string)

    def __eq__(self, other):
        return self.string == other.string

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(ootype.String, include_class)

    def init(self, ilasm):
        if self.string._str is None:
            ilasm.opcode('ldnull')
        else:
            ilasm.opcode('ldstr', '"%s"' % self.string._str)

class RecordConst(AbstractConst):
    def __init__(self, db, record, count):
        self.db = db
        self.cts = CTS(db)        
        self.record = record
        self.name = 'RECORD__%d' % count

    def __hash__(self):
        return hash(self.record)

    def __eq__(self, other):
        return self.record == other.record

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.record._TYPE, include_class)

    def init(self, ilasm):
        class_name = self.get_type(False)
        ilasm.new('instance void class %s::.ctor()' % class_name)
        for f_name, (FIELD_TYPE, f_default) in self.record._TYPE._fields.iteritems():
            f_type = self.cts.lltype_to_cts(FIELD_TYPE)
            value = self.record._items[f_name]
            ilasm.opcode('dup')
            AbstractConst.load(self.db, FIELD_TYPE, value, ilasm)            
            ilasm.set_field((f_type, class_name, f_name))

class StaticMethodConst(AbstractConst):
    def __init__(self, db, sm, count):
        self.db = db
        self.cts = CTS(db)
        self.sm = sm
        self.name = 'DELEGATE__%d' % count

    def __hash__(self):
        return hash(self.sm)

    def __eq__(self, other):
        return self.sm == other.sm

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.sm._TYPE, include_class)

    def init(self, ilasm):
        if self.sm is ootype.null(self.sm._TYPE):
            ilasm.opcode('ldnull')
            return
        self.db.pending_function(self.sm.graph)
        signature = self.cts.graph_to_signature(self.sm.graph)
        delegate_type = self.db.record_delegate_type(self.sm._TYPE)
        ilasm.opcode('ldnull')
        ilasm.opcode('ldftn', signature)
        ilasm.new('instance void class %s::.ctor(object, native int)' % delegate_type)

class ClassConst(AbstractConst):
    def __init__(self, db, class_, count):
        self.db = db
        self.cts = CTS(db)
        self.class_ = class_
        self.name = 'CLASS__%d' % count

    def __hash__(self):
        return hash(self.class_)

    def __eq__(self, other):
        return self.class_ == other.class_

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.class_._TYPE, include_class)

    def init(self, ilasm):
        INSTANCE = self.class_._INSTANCE
        if INSTANCE is None:
            ilasm.opcode('ldnull')
        else:
            self.cts.lltype_to_cts(INSTANCE) # force scheduling class generation
            ilasm.opcode('ldtoken', INSTANCE._name)
            ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')

class ListConst(AbstractConst):
    def __init__(self, db, list_, count):
        self.db = db
        self.cts = CTS(db)
        self.list = list_
        self.name = 'LIST__%d' % count

    def __hash__(self):
        return hash(self.list)

    def __eq__(self, other):
        return self.list == other.list

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.list._TYPE, include_class)

    def init(self, ilasm):
        if not self.list: # it is a null list
            ilasm.opcode('ldnull')
            return

        class_name = self.get_type(False)
        ITEMTYPE = self.list._TYPE._ITEMTYPE
        itemtype = self.cts.lltype_to_cts(ITEMTYPE)
        itemtype_T = self.cts.lltype_to_cts(self.list._TYPE.ITEMTYPE_T)
        ilasm.new('instance void class %s::.ctor()' % class_name)

        # special case: List(Void); only resize it, don't care of the contents
        if ITEMTYPE is ootype.Void:
            ilasm.opcode('dup')
            AbstractConst.load(self.db, ootype.Signed, len(self.list._list), ilasm)            
            meth = 'void class %s::_ll_resize(int32)' % PYPY_LIST_OF_VOID
            ilasm.call_method(meth, False)
            return
        
        for item in self.list._list:
            ilasm.opcode('dup')
            AbstractConst.load(self.db, ITEMTYPE, item, ilasm)
            meth = 'void class [pypylib]pypy.runtime.List`1<%s>::Add(%s)' % (itemtype, itemtype_T)
            ilasm.call_method(meth, False)


class InstanceConst(AbstractConst):
    def __init__(self, db, obj, static_type, count):
        self.db = db
        self.cts = CTS(db)
        self.obj = obj
        if static_type is None:
            self.static_type = obj._TYPE
        else:
            self.static_type = static_type
            self.cts.lltype_to_cts(obj._TYPE) # force scheduling of obj's class
        class_name = obj._TYPE._name.replace('.', '_')
        self.name = '%s__%d' % (class_name, count)

    def __hash__(self):
        return hash(self.obj)

    def __eq__(self, other):
        return self.obj == other.obj

    def get_type(self):
        return self.cts.lltype_to_cts(self.static_type)

    def init(self, ilasm):
        if not self.obj:
            ilasm.opcode('ldnull')
            return

        classdef = self.obj._TYPE        
        ilasm.new('instance void class %s::.ctor()' % classdef._name)
        while classdef is not None:
            for name, (TYPE, default) in classdef._fields.iteritems():
                if TYPE is ootype.Void:
                    continue
                value = getattr(self.obj, name)
                type_ = self.cts.lltype_to_cts(TYPE)
                ilasm.opcode('dup')
                AbstractConst.load(self.db, TYPE, value, ilasm)
                ilasm.opcode('stfld %s %s::%s' % (type_, classdef._name, name))
            classdef = classdef._superclass

