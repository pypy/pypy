from pypy.translator.gensupp import NameManager


class JavascriptNameManager(NameManager):
    def __init__(self):
        NameManager.__init__(self)
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

    def ensure_non_reserved(self, name):
        while name in self.reserved_names:
            name += '_'
        return name
