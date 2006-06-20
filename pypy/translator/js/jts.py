""" JavaScript type system
"""

from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype
from pypy.translator.cli import oopspec

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong, Primitive
from pypy.rpython.lltypesystem.lltype import Char, UniChar
from pypy.rpython.ootypesystem.ootype import String, _string, List, StaticMethod

from pypy.translator.js.log import log

from types import FunctionType

try:
    set
except NameError:
    from sets import Set as set

class JTS(object):
    """ Class implementing JavaScript type system
    calls with mapping similiar to cts
    """
    def __init__(self, db):
        self.db = db
    
    def __class(self, name):
        return name.replace(".", "_")
    
    def llvar_to_cts(self, var):
        return 'var ', var.name
    
    def lltype_to_cts(self, t):
        if isinstance(t, ootype.Instance):
            self.db.pending_class(t)
            return self.__class(t._name)
        elif isinstance(t, ootype.List):
            return "Array"
        elif isinstance(t, lltype.Primitive):
            return "var"
        elif isinstance(t, ootype.Record):
            return "Object"
        elif isinstance(t, ootype.String.__class__):
            return '""'
        elif isinstance(t, ootype.Dict):
            return "Object"
        #return "var"
        raise NotImplementedError("Type %r" % (t,))
    
    def graph_to_signature(self, graph, is_method = False, func_name = None):
        func_name = func_name or self.db.get_uniquename(graph,graph.name)
        
        args = graph.getargs()
        if is_method:
            args = args[1:]

        return func_name,args
    
    def method_signature(self, obj, name):
        # TODO: use callvirt only when strictly necessary
        if isinstance(obj, ootype.Instance):
            owner, meth = obj._lookup(name)
            class_name = obj._name
            return self.graph_to_signature(meth.graph, True, class_name)

        elif isinstance(obj, ootype.BuiltinType):
            meth = oopspec.get_method(obj, name)
            class_name = self.lltype_to_cts(obj)
            #arg_list = ', '.join(arg_types)
            return class_name,meth.ARGS
        else:
            assert False
    
    def obj_name(self, obj):
        return self.lltype_to_cts(obj)
    
    def primitive_repr(self, _type, v):
        if _type is Bool:
            if v == False:
                val = 'false'
            else:
                val = 'true'
        elif _type is Void:
            #if isinstance(v, FunctionType):
            #    graph = self.db.translator.annotator.bookkeeper.getdesc(v).cachedgraph(None)
            #    self.db.pending_function(graph)
            #    val = graph.name
            #else:
            val = 'undefined'
        elif isinstance(_type,String.__class__):
            val = '%r'%v._str
        elif isinstance(_type,List):
            # FIXME: It's not ok to use always empty list
            val = "[]"
        elif isinstance(_type,StaticMethod):
            self.db.pending_function(v.graph)
            val = v._name
        elif _type is UniChar or _type is Char:
            #log("Constant %r"%v)
            val = '"%s"'%str(v)
        elif isinstance(_type,Primitive):
            #log("Type: %r"%_type)
            val = str(v)
        else:
            assert False, "Unknown constant %r"%_type
            val = str(v)
        return val
    
    #def lltype_to_cts(self, t, include_class=True):
    #    return 'var'
##        if isinstance(t, ootype.Instance):
##            self.db.pending_class(t)
##            return self.__class(t._name, include_class)
##        elif isinstance(t, ootype.Record):
##            name = self.db.pending_record(t)
##            return self.__class(name, include_class)
##        elif isinstance(t, ootype.StaticMethod):
##            return 'void' # TODO: is it correct to ignore StaticMethod?
##        elif isinstance(t, ootype.List):
##            item_type = self.lltype_to_cts(t._ITEMTYPE)
##            return self.__class(PYPY_LIST % item_type, include_class)
##        elif isinstance(t, ootype.Dict):
##            key_type = self.lltype_to_cts(t._KEYTYPE)
##            value_type = self.lltype_to_cts(t._VALUETYPE)
##            return self.__class(PYPY_DICT % (key_type, value_type), include_class)
##        elif isinstance(t, ootype.DictItemsIterator):
##            key_type = self.lltype_to_cts(t._KEYTYPE)
##            value_type = self.lltype_to_cts(t._VALUETYPE)
##            return self.__class(PYPY_DICT_ITEMS_ITERATOR % (key_type, value_type), include_class)
##
##        return _get_from_dict(_lltype_to_cts, t, 'Unknown type %s' % t)
