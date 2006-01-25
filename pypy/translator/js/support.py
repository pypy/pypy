from pypy.translator.gensupp import NameManager
from pypy.translator.js.optimize import optimized_functions

class JavascriptNameManager(NameManager):
    def __init__(self, js):
        NameManager.__init__(self)
        self.js = js
        # keywords cannot be reused.  This is the C99 draft's list.
        #XXX this reserved_names list is incomplete!
        reserved_names_string = '''
                   if    then   else   function  
                   for   while  witch  continue
                   break super  var
                   bool  char   int    float
                   Array String Struct Number
                   '''
        self.reserved_names = {}
        for name in reserved_names_string.split():
            self.reserved_names[name] = True
        self.make_reserved_names(reserved_names_string)

    def uniquename(self, name):
        if self.js.compress and name != self.js.functions[0].func_name and name not in optimized_functions and name != "ll_issubclass__object_vtablePtr_object_vtablePtr":
            name = 'f'
        return NameManager.uniquename(self, name)

    def ensure_non_reserved(self, name):
        while name in self.reserved_names:
            name += '_'
        return name
