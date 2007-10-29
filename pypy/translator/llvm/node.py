from pypy.rpython.lltypesystem import lltype

class Node(object):
    __slots__ = "name".split()
    prefix = '%'

    nodename_count = {}

    def make_name(self, name=''):
        " helper for creating names"
        name = self.prefix + name
        if name in self.nodename_count:
            postfix = '_%d' % self.nodename_count[name]
            self.nodename_count[name] += 1
        else:
            postfix = ''
            self.nodename_count[name] = 1
        name += postfix

        if " " in name or "<" in name: 
            name = '"%s"' % name

        self.name = name

    def setup(self):
        pass

    def post_setup_transform(self):
        pass

    def external_c_source(self):
        " return a list of unique includes and sources in C "
        return [], []
    
    def writesetupcode(self, codewriter):
        " pre entry-point setup "
        pass

    @property
    def ref(self):
        return self.name

    def __str__(self):
        return "<%s %r>" % (self.__class__.__name__, self.ref)

class FuncNode(Node):

    # XXX proof that the whole llvm is hanging on a bunch of loose stitches 
    def get_ref(self):
        return self.ref

    # XXX proof that the whole llvm is hanging on a bunch of loose stitches 
    def get_pbcref(self, _):
        return self.ref

    def writedecl(self, codewriter):
        " write function forward declarations "
        pass

    def writeimpl(self, codewriter):
        """ write function implementations """ 
        pass
    
class ConstantNode(Node):
    __slots__ = "".split()

    def get_ref(self):
        # XXX tmp 
        return self.ref

    def get_childref(self, index):
        """ Returns a reference as used for operations in blocks for internals of a pbc. """
        raise AttributeError("Must be implemented in subclass")

    def get_pbcref(self, toptr):
        """ Returns a reference as a pointer used per pbc. """        
        return self.ref

    # ______________________________________________________________________
    # entry points from genllvm

    def constantvalue(self):
        """ Returns the constant representation for this node. """
        pass

    def writeglobalconstants(self, codewriter):
        p, c = lltype.parentlink(self.value)
        if p is None:
            codewriter.globalinstance(self.ref, self.constantvalue())
        

