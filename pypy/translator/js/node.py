from pypy.rpython.lltypesystem import lltype


_nodename_count = {}

class Node(object):
    def reset_nodename_count():
        global _nodename_count
        _nodename_count = {}
    reset_nodename_count = staticmethod(reset_nodename_count)

    def make_name(self, name):
        " helper for creating names"
        if " " in name or "<" in name: 
            name = '"%s"' % name
        name = name.replace('.', '_')

        global _nodename_count 
        if name in _nodename_count:
            postfix = '_%d' % _nodename_count[name]
            _nodename_count[name] += 1
        else:
            postfix = ''
            _nodename_count[name] = 1
        return name + postfix

    def make_ref(self, prefix, name):
        return self.make_name(prefix + name)

    def setup(self):
        pass

    def writeglobalconstants(self, codewriter):
        """ write out global values.  """

    def writedecl(self, codewriter):
        """ write function forward declarations. """ 

    # __________________ after "implementation" ____________________
    def writeimpl(self, codewriter):
        """ write function implementations. """ 

    # __________________ output "constant's data"  ____________________
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        return []
    
    def writeglobalconstants(self, codewriter):
        p, c = lltype.parentlink(self.value)
        if p is None:
            codewriter.globalinstance( self.constantvalue() )
