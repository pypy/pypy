
""" JavaScript type system
"""

from pypy.rpython.ootypesystem import ootype

class JTS(object):
    """ Class implementing JavaScript type system
    calls with mapping similiar to cts
    """
    def __init__(self, db):
        self.db = db
    
    def llvar_to_cts(self, var):
        return 'var ', var.name
    
    def graph_to_signature(self, graph, is_method = False, func_name = None):
        ret_type, ret_var = self.llvar_to_cts(graph.getreturnvar())
        func_name = func_name or graph.name
        
        args = [arg for arg in graph.getargs() if arg.concretetype is not ootype.Void]
        if is_method:
            args = args[1:]

        #arg_types = [self.lltype_to_cts(arg.concretetype) for arg in args]
        #arg_list = ', '.join(arg_types)

        return func_name,args
    
    def lltype_to_cts(self, t, include_class=True):
        return 'var'
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
