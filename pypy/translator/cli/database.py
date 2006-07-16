from pypy.translator.cli.cts import CTS, PYPY_LIST_OF_VOID, PYPY_DICT_OF_VOID
from pypy.translator.cli.function import Function
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.record import Record
from pypy.translator.cli.delegate import Delegate
from pypy.translator.cli.comparer import EqualityComparer
from pypy.translator.cli.node import Node
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype
from pypy.translator.cli.opcodes import opcodes

try:
    set
except NameError:
    from sets import Set as set

CONST_NAMESPACE = 'pypy.runtime'
CONST_CLASS = 'Constants'

BUILTIN_RECORDS = {
    ootype.Record({"item0": ootype.Float, "item1": ootype.Signed}):
    '[pypylib]pypy.runtime.Record_Float_Signed',
    
    ootype.Record({"item0": ootype.Float, "item1": ootype.Float}):
    '[pypylib]pypy.runtime.Record_Float_Float'
    }

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
        self.delegates = {} # StaticMethod --> type_name
        self.const_names = set()
        self.name_count = 0

    def next_count(self):
        self.name_count += 1
        return self.name_count

    def pending_function(self, graph):
        function = self.function_class(self, graph)
        self.pending_node(function)
        return function.get_name()

    def pending_class(self, classdef):
        self.pending_node(Class(self, classdef))

    def pending_record(self, record):
        try:
            return BUILTIN_RECORDS[record]
        except KeyError:
            r = Record(self, record)
            self.pending_node(r)
            return r.get_name()

    def pending_node(self, node):
        if node in self._pending_nodes or node in self._rendered_nodes:
            return

        self._pending_nodes.add(node)
        node.dependencies()

    def record_function(self, graph, name):
        self.functions[graph] = name

    def record_class(self, classdef, name):
        self.classes[classdef] = name

    def graph_name(self, graph):
        # XXX: graph name are not guaranteed to be unique
        return self.functions.get(graph, None)

    def class_name(self, classdef):
        return self.classes.get(classdef, None)

    def get_record_name(self, RECORD):
        try:
            return BUILTIN_RECORDS[RECORD]
        except KeyError:
            r = Record(self, RECORD)
            return r.get_name() # TODO: cache the result?

    def record_const(self, value):
        if value in self.consts:
            const = self.consts[value]
        else:
            const = AbstractConst.make(self, value, self.next_count())
            self.consts[value] = const
            self.pending_node(const)

        return '%s.%s::%s' % (CONST_NAMESPACE, CONST_CLASS, const.name)

    def record_delegate(self, TYPE):
        try:
            return self.delegates[TYPE]
        except KeyError:
            name = 'StaticMethod__%d' % len(self.delegates)
            self.delegates[TYPE] = name
            self.pending_node(Delegate(self, TYPE, name))
            return name

    def gen_constants(self, ilasm):
        ilasm.begin_namespace(CONST_NAMESPACE)
        ilasm.begin_class(CONST_CLASS)

        # render field definitions
        for const in self.consts.itervalues():
            ilasm.field(const.name, const.get_type(), static=True)

        ilasm.begin_function('.cctor', [], 'void', False, 'static',
            'specialname', 'rtspecialname', 'default')

        # this point we have collected all constant we
        # need. Instantiate&initialize them.
        for const in self.consts.itervalues():
            type_ = const.get_type()
            const.instantiate(ilasm)
            ilasm.store_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)

        for const in self.consts.itervalues():
            type_ = const.get_type()
            ilasm.load_static_constant(type_, CONST_NAMESPACE, CONST_CLASS, const.name)
            const.init(ilasm)

        ilasm.ret()
        ilasm.end_function()

        ilasm.end_class()
        ilasm.end_namespace()


class AbstractConst(Node):
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
        elif isinstance(value, ootype._static_meth):
            return StaticMethodConst(db, value, count)
        elif isinstance(value, ootype._class):
            return ClassConst(db, value, count)
        elif isinstance(value, ootype._custom_dict):
            return CustomDictConst(db, value, count)
        elif isinstance(value, ootype._dict):
            return DictConst(db, value, count)
        else:
            assert False, 'Unknown constant: %s' % value
    make = staticmethod(make)

    PRIMITIVE_TYPES = set([ootype.Void, ootype.Bool, ootype.Char, ootype.UniChar,
                           ootype.Float, ootype.Signed, ootype.Unsigned, ootype.String,
                           lltype.SignedLongLong, lltype.UnsignedLongLong])

    def is_primitive(cls, TYPE):
        return TYPE in cls.PRIMITIVE_TYPES
    is_primitive = classmethod(is_primitive)

    def load(cls, db, TYPE, value, ilasm):
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
        elif TYPE is ootype.String:
            if value._str is None:
                ilasm.opcode('ldnull')
            else:
                s = value._str
                s = '"%s"' % s.replace('"', '\\"')
                ilasm.opcode("ldstr", s)
        else:
            assert TYPE not in cls.PRIMITIVE_TYPES
            cts = CTS(db)
            name = db.record_const(value)
            cts_type = cts.lltype_to_cts(TYPE)
            ilasm.opcode('ldsfld %s %s' % (cts_type, name))
    load = classmethod(load)

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '<Const %s %s>' % (self.name, self.value)

    def get_name(self):
        pass

    def get_type(self):
        pass

    def record_const_maybe(self, TYPE, value):
        if AbstractConst.is_primitive(TYPE):
            return
        self.db.record_const(value)

    def render(self, ilasm):
        pass

    def dependencies(self):
        """
        Record all constants that are needed to correctly initialize
        the object.
        """

    def instantiate(self, ilasm):
        """
        Instantiate the the object which represent the constant and
        leave a reference to it on the stack.
        """
        raise NotImplementedError

    def init(self, ilasm):
        """
        Do some sort of extra initialization, if needed. It assume the
        object to be initialized is on the stack. Don't leave anything
        on the stack.
        """
        ilasm.opcode('pop')


class RecordConst(AbstractConst):
    def __init__(self, db, record, count):
        self.db = db
        self.cts = CTS(db)        
        self.value = record
        self.name = 'RECORD__%d' % count

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.value._TYPE, include_class)

    def dependencies(self):
        if self.value is ootype.null(self.value._TYPE):
            return
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            value = self.value._items[f_name]            
            self.record_const_maybe(FIELD_TYPE, value)

    def instantiate(self, ilasm):
        if self.value is ootype.null(self.value._TYPE):
            ilasm.opcode('ldnull')
            return

        class_name = self.get_type(False)
        ilasm.new('instance void class %s::.ctor()' % class_name)

    def init(self, ilasm):
        if self.value is ootype.null(self.value._TYPE):
            ilasm.opcode('pop')
            return
        class_name = self.get_type(False)        
        for f_name, (FIELD_TYPE, f_default) in self.value._TYPE._fields.iteritems():
            if FIELD_TYPE is not ootype.Void:
                f_type = self.cts.lltype_to_cts(FIELD_TYPE)
                value = self.value._items[f_name]
                ilasm.opcode('dup')
                AbstractConst.load(self.db, FIELD_TYPE, value, ilasm)            
                ilasm.set_field((f_type, class_name, f_name))
        ilasm.opcode('pop')

class StaticMethodConst(AbstractConst):
    def __init__(self, db, sm, count):
        self.db = db
        self.cts = CTS(db)
        self.value = sm
        self.name = 'DELEGATE__%d' % count

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.value._TYPE, include_class)

    def dependencies(self):
        if self.value is ootype.null(self.value._TYPE):
            return
        self.db.pending_function(self.value.graph)
        self.delegate_type = self.db.record_delegate(self.value._TYPE)

    def instantiate(self, ilasm):
        if self.value is ootype.null(self.value._TYPE):
            ilasm.opcode('ldnull')
            return
        signature = self.cts.graph_to_signature(self.value.graph)
        ilasm.opcode('ldnull')
        ilasm.opcode('ldftn', signature)
        ilasm.new('instance void class %s::.ctor(object, native int)' % self.delegate_type)

class ClassConst(AbstractConst):
    def __init__(self, db, class_, count):
        self.db = db
        self.cts = CTS(db)
        self.value = class_
        self.name = 'CLASS__%d' % count

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.value._TYPE, include_class)

    def dependencies(self):
        INSTANCE = self.value._INSTANCE
        if INSTANCE is not None:
            self.cts.lltype_to_cts(INSTANCE) # force scheduling class generation

    def instantiate(self, ilasm):
        INSTANCE = self.value._INSTANCE
        if INSTANCE is None:
            ilasm.opcode('ldnull')
        else:
            ilasm.opcode('ldtoken', INSTANCE._name)
            ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')

class ListConst(AbstractConst):
    def __init__(self, db, list_, count):
        self.db = db
        self.cts = CTS(db)
        self.value = list_
        self.name = 'LIST__%d' % count

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.value._TYPE, include_class)

    def dependencies(self):
        if not self.value:
            return
        for item in self.value._list:
            self.record_const_maybe(self.value._TYPE._ITEMTYPE, item)

    def instantiate(self, ilasm):
        if not self.value: # it is a null list
            ilasm.opcode('ldnull')
            return

        class_name = self.get_type(False)
        ilasm.new('instance void class %s::.ctor()' % class_name)

    def init(self, ilasm):
        if not self.value:
            ilasm.opcode('pop')
            return

        ITEMTYPE = self.value._TYPE._ITEMTYPE
        itemtype = self.cts.lltype_to_cts(ITEMTYPE)
        itemtype_T = self.cts.lltype_to_cts(self.value._TYPE.ITEMTYPE_T)

        # special case: List(Void); only resize it, don't care of the contents
        if ITEMTYPE is ootype.Void:
            AbstractConst.load(self.db, ootype.Signed, len(self.value._list), ilasm)            
            meth = 'void class %s::_ll_resize(int32)' % PYPY_LIST_OF_VOID
            ilasm.call_method(meth, False)
            return
        
        for item in self.value._list:
            ilasm.opcode('dup')
            AbstractConst.load(self.db, ITEMTYPE, item, ilasm)
            meth = 'void class [pypylib]pypy.runtime.List`1<%s>::Add(%s)' % (itemtype, itemtype_T)
            ilasm.call_method(meth, False)
        ilasm.opcode('pop')

class DictConst(AbstractConst):
    def __init__(self, db, dict_, count):
        self.db = db
        self.cts = CTS(db)
        self.value = dict_
        self.name = 'DICT__%d' % count

    def get_type(self, include_class=True):
        return self.cts.lltype_to_cts(self.value._TYPE, include_class)

    def dependencies(self):
        if not self.value:
            return
        
        for key, value in self.value._dict.iteritems():
            self.record_const_maybe(self.value._TYPE._KEYTYPE, key)
            self.record_const_maybe(self.value._TYPE._VALUETYPE, value)

    def instantiate(self, ilasm):
        if not self.value: # it is a null dict
            ilasm.opcode('ldnull')
            return

        class_name = self.get_type(False)
        ilasm.new('instance void class %s::.ctor()' % class_name)
        
    def init(self, ilasm):
        if not self.value:
            ilasm.opcode('pop')
            return
        
        class_name = self.get_type(False)
        KEYTYPE = self.value._TYPE._KEYTYPE
        keytype = self.cts.lltype_to_cts(KEYTYPE)
        keytype_T = self.cts.lltype_to_cts(self.value._TYPE.KEYTYPE_T)

        VALUETYPE = self.value._TYPE._VALUETYPE
        valuetype = self.cts.lltype_to_cts(VALUETYPE)
        valuetype_T = self.cts.lltype_to_cts(self.value._TYPE.VALUETYPE_T)

        if KEYTYPE is ootype.Void:
            assert VALUETYPE is ootype.Void
            ilasm.opcode('pop')
            return

        # special case: dict of void, ignore the values
        if VALUETYPE is ootype.Void:
            class_name = PYPY_DICT_OF_VOID % keytype
            for key in self.value._dict:
                ilasm.opcode('dup')
                AbstractConst.load(self.db, KEYTYPE, key, ilasm)
                meth = 'void class %s::ll_set(%s)' % (class_name, keytype_T)
                ilasm.call_method(meth, False)
            ilasm.opcode('pop')
            return

        for key, value in self.value._dict.iteritems():
            ilasm.opcode('dup')
            AbstractConst.load(self.db, KEYTYPE, key, ilasm)
            AbstractConst.load(self.db, VALUETYPE, value, ilasm)
            meth = 'void class [pypylib]pypy.runtime.Dict`2<%s, %s>::ll_set(%s, %s)' %\
                   (keytype, valuetype, keytype_T, valuetype_T)
            ilasm.call_method(meth, False)
        ilasm.opcode('pop')

class CustomDictConst(DictConst):
    def dependencies(self):
        if not self.value:
            return

        eq = self.value._dict.key_eq
        hash = self.value._dict.key_hash
        self.comparer = EqualityComparer(self.db, self.value._TYPE._KEYTYPE, eq, hash)
        self.db.pending_node(self.comparer)
        DictConst.dependencies(self)

    def instantiate(self, ilasm):
        if not self.value: # it is a null dict
            ilasm.opcode('ldnull')
            return

        ilasm.new(self.comparer.get_ctor())
        class_name = self.get_type()
        ilasm.new('instance void %s::.ctor(class '
                  '[mscorlib]System.Collections.Generic.IEqualityComparer`1<!0>)'
                  % class_name)


class InstanceConst(AbstractConst):
    def __init__(self, db, obj, static_type, count):
        self.db = db
        self.cts = CTS(db)
        self.value = obj
        if static_type is None:
            self.static_type = obj._TYPE
        else:
            self.static_type = static_type
            self.cts.lltype_to_cts(obj._TYPE) # force scheduling of obj's class
        class_name = obj._TYPE._name.replace('.', '_')
        self.name = '%s__%d' % (class_name, count)

    def get_type(self):
        return self.cts.lltype_to_cts(self.static_type)

    def dependencies(self):
        if not self.value:
            return

        INSTANCE = self.value._TYPE
        while INSTANCE is not None:
            for name, (TYPE, default) in INSTANCE._fields.iteritems():
                if TYPE is ootype.Void:
                    continue
                type_ = self.cts.lltype_to_cts(TYPE) # record type
                value = getattr(self.value, name) # record value
                self.record_const_maybe(TYPE, value)
            INSTANCE = INSTANCE._superclass                

    def instantiate(self, ilasm):
        if not self.value:
            ilasm.opcode('ldnull')
            return

        classdef = self.value._TYPE        
        ilasm.new('instance void class %s::.ctor()' % classdef._name)

    def init(self, ilasm):
        if not self.value:
            ilasm.opcode('pop')
            return

        INSTANCE = self.value._TYPE
        while INSTANCE is not None:
            for name, (TYPE, default) in INSTANCE._fields.iteritems():
                if TYPE is ootype.Void:
                    continue
                value = getattr(self.value, name)
                type_ = self.cts.lltype_to_cts(TYPE)
                ilasm.opcode('dup')
                AbstractConst.load(self.db, TYPE, value, ilasm)
                ilasm.opcode('stfld %s %s::%s' % (type_, INSTANCE._name, name))
            INSTANCE = INSTANCE._superclass
        ilasm.opcode('pop')
