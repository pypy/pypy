
""" genjs constant database module
"""

from pypy.rpython.ootypesystem import ootype
from pypy.translator.js2.opcodes import opcodes
from pypy.translator.js2.function import Function
from pypy.translator.js2.log import log
from pypy.translator.js2.jts import JTS
from pypy.translator.js2._class import Class
from pypy.translator.js2.support import JavascriptNameManager

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong, typeOf
from pypy.rpython.lltypesystem.lltype import Char, UniChar
from pypy.rpython.ootypesystem import ootype

from pypy.objspace.flow.model import Variable, Constant

try:
    set
except NameError:
    from sets import Set as set

class LowLevelDatabase(object):
    def __init__(self, type_system_class = JTS, opcode_dict = opcodes, function_class = Function):
        self._pending_nodes = set()
        self.opcode_dict = opcode_dict
        self._rendered_nodes = set()
        self.function_class = function_class
        self.type_system_class = type_system_class
        self.classes = {} # classdef --> class_name
        self.functions = {} # graph --> function_name
        self.function_names = {} # graph --> real_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> const_name
        self.const_names = set()
        self.const_var = Variable("__consts")
        self.name_manager = JavascriptNameManager(self)
        self.pending_consts = []
        self.cts = type_system_class(self)

    def is_primitive(self, type_):
        if type_ in [Void, Bool, Float, Signed, Unsigned, SignedLongLong, UnsignedLongLong, Char, UniChar] or \
            isinstance(type_,ootype.StaticMethod):
            return True
        return False

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
    
    def get_uniquename(self, graph, name):
        try:
            return self.function_names[graph]
        except KeyError:
            real_name = self.name_manager.uniquename(name)
            self.function_names[graph] = real_name
            return real_name

    def record_class(self, classdef, name):
        self.classes[classdef] = name

    def graph_name(self, graph):
        return self.functions.get(graph, None)

    def class_name(self, classdef):
        return self.classes.get(classdef, None)

    def record_const(self, value, retval='name'):
        type_ = typeOf(value)
        if self.is_primitive(type_):
            return None
        const = AbstractConst.make(self, value)
        try:
            return self.consts[const]
        except KeyError:
            log("New const:%r"%value)
            if isinstance(value, ootype._string):
                log(value._str)
            name = const.get_name()
            if name in self.const_names:
                name += '__%d' % len(self.consts)
            self.consts[const] = name
            self.const_names.add(name)
            self.pending_consts.append((const,name))
        if retval == 'name':
            return name
        else:
            return const

    def gen_constants(self, ilasm):
        ilasm.begin_consts(self.const_var.name)
        
        try:
            while True:
                const,name = self.pending_consts.pop()
                const.record_fields()
        except IndexError:
            pass
        

        def generate_constants(consts):
            all_c = [const for const,name in consts.iteritems()]
            rendered = set()
            
            while len(all_c) > 0:
                const = all_c.pop()
                if const not in rendered:
                    if (not hasattr(const,'depends')) or (not const.depends):
                        yield const,consts[const]
                        rendered.add(const)
                    else:
                        all_c.append(const)
                        for i in const.depends:
                            const.depends = None
                            all_c.append(i)

        # We need to keep track of fields to make sure
        # our items appear earlier than us
        for const,name in generate_constants(self.consts):
            log("Recording %r %r"%(const,name))
            ilasm.load_local(self.const_var)
            const.init(ilasm)
            ilasm.set_field(None, name)
            ilasm.store_void()
            const.init_fields(ilasm, self.const_var, name)
            #ilasm.field(name, const.get_type(), static=True)
        
    
    def load_const(self, type_, value, ilasm):
        if self.is_primitive(type_):
            ilasm.load_const(self.cts.primitive_repr(type_, value))
        else:
            name = self.record_const(value)
            ilasm.load_local(self.const_var)
            ilasm.get_field(name)
            #assert False, 'Unknown constant %s' % const


class AbstractConst(object):
    def __init__(self, db, const):
        self.db = db
        self.const = const
        self.cts = db.type_system_class(db)
        self.depends = set()
    
    def make(db, const):
        if isinstance(const, ootype._view):
            static_type = const._TYPE
            const = const._inst
        else:
            static_type = None

        if isinstance(const, ootype._instance):
            return InstanceConst(db, const, static_type)
        elif isinstance(const, ootype._list):
            return ListConst(db, const)
        elif isinstance(const, ootype._record):
            return RecordConst(db, const)
        elif isinstance(const, ootype._string):
            return StringConst(db, const)
        else:
            assert False, 'Unknown constant: %s %r' % (const, typeOf(const))
    make = staticmethod(make)

    def get_name(self):
        pass

    def get_type(self):
        pass

    def init(self, ilasm):
        pass
    
    def init_fields(self, ilasm, const_var, name):
        pass
    
    def record_fields(self):
        pass

class InstanceConst(AbstractConst):
    def __init__(self, db, obj, static_type):
        self.depends = set()
        self.db = db
        self.cts = db.type_system_class(db)
        self.obj = obj
        if static_type is None:
            self.static_type = obj._TYPE
        else:
            self.static_type = static_type
            self.cts.lltype_to_cts(obj._TYPE) # force scheduling of obj's class

    def __hash__(self):
        return hash(self.obj)

    def __eq__(self, other):
        return self.obj == other.obj

    def get_name(self):
        return self.obj._TYPE._name.replace('.', '_')

    def get_type(self):
        return self.cts.lltype_to_cts(self.static_type)

    def init(self, ilasm):
        classdef = self.obj._TYPE
        ilasm.new(classdef._name.split(".")[-1])
    
    def record_fields(self):
        # we support only primitives, tuples, strings and lists
        for i in self.obj.__dict__:
            # FIXME: is this ok?
            if i.startswith('o'):
                val = self.obj.__dict__[i]
                name = self.db.record_const(val,'const')
                if name is not None:
                    self.depends.add(name)
    
    def init_fields(self, ilasm, const_var, name):
        for i in self.obj.__dict__:
            # FIXME: is this ok?
            if i.startswith('o'):
                ilasm.load_local(const_var)
                el = self.obj.__dict__[i]
                self.db.load_const(typeOf(el), el, ilasm)
                ilasm.set_field(None, "%s.%s"%(name, i))
                ilasm.store_void()
        #raise NotImplementedError("Default fields of instances")

class RecordConst(AbstractConst):
    def get_name(self):
        return "const_tuple"
    
    def init(self, ilasm):
        ilasm.new_obj()
    
    def record_fields(self):
        for i in self.const._items:
            name = self.db.record_const(self.const._items[i],'const')
            if name is not None:
                self.depends.add(name)
    
    def __hash__(self):
        return hash(self.const)
    
    def __eq__(self, other):
        return self.const == other.const

    def init_fields(self, ilasm, const_var, name):
        #for i in self.const.__dict__["_items"]:
        for i in self.const._items:
            ilasm.load_local(const_var)
            el = self.const._items[i]
            self.db.load_const(typeOf(el), el, ilasm)
            ilasm.set_field(None, "%s.%s"%(name, i))
            ilasm.store_void()

class ListConst(AbstractConst):
    
    def get_name(self):
        return "const_list"
    
    def init(self, ilasm):
        ilasm.new_list()
    
    def record_fields(self):
        for i in self.const._list:
            name = self.db.record_const(i,'const')
            if name is not None:
                self.depends.add(name)

    def __hash__(self):
        return hash(self.const)
    
    def __eq__(self, other):
        return self.const == other.const

    def init_fields(self, ilasm, const_var, name):
        for i in xrange(len(self.const._list)):
            ilasm.load_str("%s.%s"%(const_var.name, name))
            el = self.const._list[i]
            self.db.load_const(typeOf(el), el, ilasm)
            self.db.load_const(typeOf(i), i, ilasm)
            ilasm.list_setitem()
            ilasm.store_void()

class StringConst(AbstractConst):
    def get_name(self):
        return "const_str"

    def __hash__(self):
        return hash(self.const._str)
    
    def __eq__(self, other):
        return self.const._str == other.const._str

    def init(self, ilasm):
        ilasm.load_str("'%s'"%self.const._str)
    
    def init_fields(self, ilasm, const_var, name):
        pass

##        ilasm.new('instance void class %s::.ctor()' % classdef._name)
##        while classdef is not None:
##            for name, (type_, default) in classdef._fields.iteritems():
##                if isinstance(type_, ootype.StaticMethod):
##                    continue
##                elif type_ is ootype.Class:
##                    value = getattr(self.obj, name)
##                    self.cts.lltype_to_cts(value._INSTANCE) # force scheduling class generation
##                    classname = value._INSTANCE._name
##                    ilasm.opcode('dup')
##                    ilasm.opcode('ldtoken', classname)
##                    ilasm.call('class [mscorlib]System.Type class [mscorlib]System.Type::GetTypeFromHandle(valuetype [mscorlib]System.RuntimeTypeHandle)')
##                    ilasm.opcode('stfld class [mscorlib]System.Type %s::%s' % (classdef._name, name))
##            classdef = classdef._superclass
##
