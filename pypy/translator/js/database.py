
""" genjs constant database module
"""

from pypy.rpython.ootypesystem import ootype
from pypy.translator.js.opcodes import opcodes
from pypy.translator.js.function import Function
from pypy.translator.js.log import log
from pypy.translator.js.jts import JTS
from pypy.translator.js._class import Class
from pypy.translator.js.support import JavascriptNameManager

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong, typeOf
from pypy.rpython.lltypesystem.lltype import Char, UniChar
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import bltregistry

from pypy.objspace.flow.model import Variable, Constant
from pypy.translator.js.modules import dom
from pypy.translator.js.commproxy import XmlHttp

try:
    set
except NameError:
    from sets import Set as set

class LowLevelDatabase(object):
    def __init__(self, backend_mapping = None):
        self._pending_nodes = set()
        self.opcode_dict = backend_mapping['opcode_dict']
        self._rendered_nodes = set()
        self.function_class = backend_mapping['function_class']
        self.type_system_class = backend_mapping['type_system_class']
        self.classes = {} # classdef --> class_name
        self.functions = {} # graph --> function_name
        self.function_names = {} # graph --> real_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> const_name
        self.const_names = set()
        self.const_var = Variable("__consts")
        self.name_manager = JavascriptNameManager(self)
        self.pending_consts = []
        self.backend_mapping = backend_mapping
        self.cts = self.type_system_class(self)
        self.prepare_builtins()
        self.proxies = []
    
    def prepare_builtins(self):
        # Document Object Model elements
        #for module in [dom]:
        #    for i in dir(module):
        #        if not i.startswith('__'):
        #            # FIXME: shit, strange way of doing it
        #            self.consts[BuiltinConst(module[i])] = i
        return

    def is_primitive(self, type_):
        if type_ in [Void, Bool, Float, Signed, Unsigned, SignedLongLong, UnsignedLongLong, Char, UniChar] or \
            isinstance(type_,ootype.StaticMethod):
            return True
        return False

    def pending_function(self, graph):
        self.pending_node(self.function_class(self, graph))

    def pending_class(self, classdef):
        c = Class(self, classdef)
        self.pending_node(c)
        return c

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
    
    def register_comm_proxy(self, proxy_const, name):
        """ Register external object which should be rendered as
        method call
        """
        self.proxies.append(XmlHttp(proxy_const, name))

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
            if retval == 'name':
                return self.consts[const]
            else:
                self.consts[const]
                return const
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

        log("Consts: %r"%self.consts)
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
            try:
                return self.consts[BuiltinConst(value)]
            except KeyError:
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
    
    def __ne__(self, other):
        return not (self == other)
    
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
        elif isinstance(const, ootype._dict):
            return DictConst(db, const)
        elif isinstance(const, bltregistry._external_type):
            return ExtObject(db, const)
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
        try:
            classdef._hints['_suggested_external']
            ilasm.new(classdef._name.split(".")[-1])
        except KeyError:
            ilasm.new(classdef._name.replace(".", "_"))
    
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
        s = self.const._str
        # do some escaping
        s = s.replace("\n", "\\n")
        ilasm.load_str('"%s"'%s)
    
    def init_fields(self, ilasm, const_var, name):
        pass

class BuiltinConst(AbstractConst):
    def __init__(self, name):
        self.name = name
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        return self.name == other.name
    
    def get_name(self):
        return self.name
    
    def init_fields(self, *args):
        pass
    
    def init(self, ilasm):
        ilasm.load_str(self.name)

class DictConst(RecordConst):
    def record_fields(self):
        for i in self.const._dict:
            name = self.db.record_const(self.const._dict[i],'const')
            if name is not None:
                self.depends.add(name)

    def init_fields(self, ilasm, const_var, name):
        for i in self.const._dict:
            ilasm.load_str("%s.%s"%(const_var.name, name))
            el = self.const._dict[i]
            self.db.load_const(typeOf(el), el, ilasm)
            self.db.load_const(typeOf(i), i, ilasm)
            ilasm.list_setitem()
            ilasm.store_void()

class ExtObject(AbstractConst):
    def __init__(self, db, const):
        self.db = db
        self.const = const
        self.name = self.get_name()
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)
    
    def get_name(self):
        return self.const._TYPE._name.split('.')[-1][:-2]
    
    def init(self, ilasm):
        if getattr(self.const._TYPE._class_, '_render_xmlhttp', False):
            self.db.register_comm_proxy(self.const, self.name)
            ilasm.new(self.get_name())
        else:
            # Otherwise they just exist, or it's not implemented
            pass

