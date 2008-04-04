
""" genjs constant database module
"""

import py
from pypy.rpython.ootypesystem import ootype
from pypy.translator.js.opcodes import opcodes
from pypy.translator.js.function import Function
from pypy.translator.js.log import log
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
    def __init__(self, genoo):
        self._pending_nodes = set()
        self.genoo = genoo
        self._rendered_nodes = set()
        self.classes = {} # classdef --> class_name
        self.functions = {} # graph --> function_name
        self.function_names = {} # graph --> real_name
        self.methods = {} # graph --> method_name
        self.consts = {}  # value --> const_name
        self.reverse_consts = {}
        self.const_names = set()
        self.rendered = set()
        self.const_var = Variable("__consts")
        self.name_manager = JavascriptNameManager(self)
        self.pending_consts = []
        self.cts = self.genoo.TypeSystem(self)
        self.proxies = []
    
    def is_primitive(self, type_):
        if type_ in [Void, Bool, Float, Signed, Unsigned, SignedLongLong, UnsignedLongLong, Char, UniChar, ootype.StringBuilder] or \
            isinstance(type_,ootype.StaticMethod):
            return True
        return False

    def pending_function(self, graph):
        self.pending_node(self.genoo.Function(self, graph))

    def pending_abstract_function(self, name):
        pass
        # XXX we want to implement it at some point (maybe...)

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
            real_name = self.name_manager.uniquename(name, lenmax=1111111)
            self.function_names[graph] = real_name
            return real_name

    def record_class(self, classdef, name):
        self.classes[classdef] = name
    
    def register_comm_proxy(self, proxy_const, *args):
        """ Register external object which should be rendered as
        method call
        """
        self.proxies.append(XmlHttp(proxy_const, *args))

    def graph_name(self, graph):
        return self.functions.get(graph, None)

    def class_name(self, classdef):
        return self.classes.get(classdef, None)

    def record_const(self, value, type_ = None, retval='name'):
        if type_ is None:
            type_ = typeOf(value)
        if self.is_primitive(type_):
            return None
        const = AbstractConst.make(self, value)
        if not const:
            return None
        try:
            if retval == 'name':
                return self.consts[const]
            else:
                self.consts[const]
                return self.reverse_consts[self.consts[const]]
        except KeyError:
            if self.genoo.config.translation.verbose:
                log("New const:%r"%value)
                if isinstance(value, ootype._string):
                    log(value._str)
            else:
                log.dot()
            name = const.get_name()
            if name in self.const_names:
                name += '__%d' % len(self.consts)
            self.consts[const] = name
            self.reverse_consts[name] = const
            self.const_names.add(name)
            self.pending_consts.append((const,name))
        if retval == 'name':
            return name
        else:
            return const

    def gen_constants(self, ilasm, pending):
        try:
            while True:
                const,name = self.pending_consts.pop()
                const.record_fields()
        except IndexError:
            pass

        if pending:
            return

        if not self.rendered:
            ilasm.begin_consts(self.const_var.name)
        
        def generate_constants(consts):
            all_c = [const for const,name in consts.iteritems()]
            dep_ok = set()
            while len(all_c) > 0:
                const = all_c.pop()
                if const not in self.rendered:
                    to_render = True
                    if hasattr(const, 'depends_on') and const.depends_on:
                        for i in const.depends_on:
                            if i not in self.rendered and i not in dep_ok:
                                assert i.depends is None or const in i.depends
                                to_render = False
                                continue
                    
                    if to_render and (not hasattr(const, 'depends')) or (not const.depends) or const in dep_ok:
                        yield const,consts[const]
                        self.rendered.add(const)
                    else:
                        all_c.append(const)
                        for i in const.depends:
                            all_c.append(i)
                        dep_ok.add(const)

        # We need to keep track of fields to make sure
        # our items appear earlier than us
        to_init = []
        for const, name in generate_constants(self.consts):
            if self.genoo.config.translation.verbose:
                log("Recording %r %r"%(const,name))
            else:
                log.dot()
            ilasm.load_local(self.const_var)
            const.init(ilasm)
            ilasm.set_field(None, name)
            ilasm.store_void()
            to_init.append((const, name))
            #ilasm.field(name, const.get_type(), static=True)
        for const, name in to_init:
            const.init_fields(ilasm, self.const_var, name)

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
        self.cts = db.genoo.TypeSystem(db)
        self.depends = set()
        self.depends_on = set()

    def __hash__(self):
        return hash(self.get_key())

    def __eq__(self, other):
        return (other.__class__ is self.__class__ and
                other.get_key() == self.get_key())

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
        elif isinstance(const, ootype._array):
            return ListConst(db, const)
        elif isinstance(const, ootype._record):
            return RecordConst(db, const)
        elif isinstance(const, ootype._string):
            return StringConst(db, const)
        elif isinstance(const, ootype._dict):
            return DictConst(db, const)
        elif isinstance(const, bltregistry._external_inst):
            return ExtObject(db, const)
        elif isinstance(const, ootype._class):
            if const._INSTANCE:
                return ClassConst(db, const)
            else:
                return None
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
        self.depends_on = set()
        self.db = db
        self.cts = db.genoo.TypeSystem(db)
        self.obj = obj
        if static_type is None:
            self.static_type = obj._TYPE
        else:
            self.static_type = static_type
            self.cts.lltype_to_cts(obj._TYPE) # force scheduling of obj's class

    def get_key(self):
        return self.obj

    def get_name(self):
        return self.obj._TYPE._name.replace('.', '_')

    def get_type(self):
        return self.cts.lltype_to_cts(self.static_type)

    def init(self, ilasm):
        if not self.obj:
            ilasm.load_void()
            return
        
        classdef = self.obj._TYPE
        try:
            classdef._hints['_suggested_external']
            ilasm.new(classdef._name.split(".")[-1])
        except KeyError:
            ilasm.new(classdef._name.replace(".", "_"))
    
    def record_fields(self):
        if not self.obj:
            return
        INSTANCE = self.obj._TYPE
        #while INSTANCE:
        for i, (_type, val) in INSTANCE._allfields().items():
            if _type is not ootype.Void:
                name = self.db.record_const(getattr(self.obj, i), _type, 'const')
                if name is not None:
                    self.depends.add(name)
                    name.depends_on.add(self)
        
    def init_fields(self, ilasm, const_var, name):
        if not self.obj:
            return
        
        INSTANCE = self.obj._TYPE
        #while INSTANCE:
        for i, (_type, el) in INSTANCE._allfields().items():
            if _type is not ootype.Void:
                ilasm.load_local(const_var)
                self.db.load_const(_type, getattr(self.obj, i), ilasm)
                ilasm.set_field(None, "%s.%s"%(name, i))
                ilasm.store_void()

class RecordConst(AbstractConst):
    def get_name(self):
        return "const_tuple"
    
    def init(self, ilasm):
        if not self.const:
            ilasm.load_void()
        else:
            ilasm.new_obj()
    
    def record_fields(self):
        if not self.const:
            return
        
        for i in self.const._items:
            name = self.db.record_const(self.const._items[i], None, 'const')
            if name is not None:
                self.depends.add(name)
                name.depends_on.add(self)
    
    def get_key(self):
        return self.const

    def init_fields(self, ilasm, const_var, name):
        if not self.const:
            return
        
        #for i in self.const.__dict__["_items"]:
        for i in self.const._items:
            ilasm.load_local(const_var)
            el = self.const._items[i]
            self.db.load_const(typeOf(el), el, ilasm)
            ilasm.set_field(None, "%s.%s"%(name, i))
            ilasm.store_void()

class ListConst(AbstractConst):
    
    def _get_list(self):
        if isinstance(self.const, ootype._list):
            return self.const._list
        else:
            return self.const._array


    def get_name(self):
        return "const_list"
    
    def init(self, ilasm):
        if not self.const:
            ilasm.load_void()
        else:
            ilasm.new_list()
    
    def record_fields(self):
        if not self.const:
            return
        
        for i in self._get_list():
            name = self.db.record_const(i, None, 'const')
            if name is not None:
                self.depends.add(name)
                name.depends_on.add(self)
        
    def get_key(self):
        return self.const

    def init_fields(self, ilasm, const_var, name):
        if not self.const:
            return
        
        l = self._get_list()
        for i in xrange(len(l)):
            ilasm.load_str("%s.%s"%(const_var.name, name))
            el = l[i]
            self.db.load_const(typeOf(el), el, ilasm)
            self.db.load_const(typeOf(i), i, ilasm)
            ilasm.list_setitem()
            ilasm.store_void()

class StringConst(AbstractConst):
    def get_name(self):
        return "const_str"

    def get_key(self):
        return self.const._str

    def init(self, ilasm):
        if self.const:
            s = self.const._str
        # do some escaping
        #s = s.replace("\n", "\\n").replace('"', '\"')
        #s = repr(s).replace("\"", "\\\"")
            ilasm.load_str("%s" % repr(s))
        else:
            ilasm.load_str("undefined")
    
    def init_fields(self, ilasm, const_var, name):
        pass

class ClassConst(AbstractConst):
    def __init__(self, db, const):
        super(ClassConst, self).__init__(db, const)
        self.cts.lltype_to_cts(const._INSTANCE) # force scheduling of class
    
    def get_key(self):
        return self.get_name()
    
    def get_name(self):
        return self.const._INSTANCE._name.replace(".", "_")
    
    def init(self, ilasm):
        ilasm.load_const("%s" % self.get_name())
    
    #def init_fields(self, ilasm, const_var, name):
    #    pass

class BuiltinConst(AbstractConst):
    def __init__(self, name):
        self.name = name
    
    def get_key(self):
        return self.name
    
    def get_name(self):
        return self.name
    
    def init_fields(self, *args):
        pass
    
    def init(self, ilasm):
        ilasm.load_str(self.name)

class DictConst(RecordConst):
    def record_const(self, co):
        name = self.db.record_const(co, None, 'const')
        if name is not None:
            self.depends.add(name)
            name.depends_on.add(self)
    
    def record_fields(self):
        if not self.const:
            return
        
        for i in self.const._dict:
            self.record_const(i)
            self.record_const(self.const._dict[i])

    def init_fields(self, ilasm, const_var, name):
        if not self.const:
            return
        
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
        self.depends = set()
        self.depends_on = set()
    
    def get_key(self):
        return self.name
    
    def get_name(self):
        return self.const._TYPE._name
    
    def init(self, ilasm):
        _class = self.const._TYPE._class_
        if getattr(_class, '_render_xmlhttp', False):
            use_xml = getattr(_class, '_use_xml', False)
            base_url = getattr(_class, '_base_url', "") # XXX: should be
            method = getattr(_class, '_use_method', 'GET')
                # on per-method basis
            self.db.register_comm_proxy(self.const, self.name, use_xml, base_url, method)
            ilasm.new(self.get_name())
        else:
            # Otherwise they just exist, or it's not implemented
            if not hasattr(self.const.value, '_render_name'):
                raise ValueError("Prebuilt constant %s has no attribute _render_name,"
                                  "don't know how to render" % self.const.value)
            ilasm.load_str(self.const.value._render_name)
