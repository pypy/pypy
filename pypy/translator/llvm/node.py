from pypy.rpython.lltypesystem import lltype


class Node(object):
    __slots__ = "name".split()
    prefix = '%'

    nodename_count = {}
    def mangle(self, name):
        if name not in self.nodename_count:
            self.nodename_count[name] = 1
            return name
        else:
            result = '%s_%d' % (name, self.nodename_count[name])
            self.nodename_count[name] += 1
            # this ensures (a) doesn exist yet, and (b) adds it to the
            # dictionary just to prevent some function called xxx_42() and clashing
            return self.mangle(result)

    def make_name(self, name=''):
        " helper for creating names"
        name = self.prefix + name
        name = self.mangle(name)
        if " " in name or "<" in name: 
            name = '"%s"' % name

        self.name = name

    def setup(self):
        pass

    def writesetupcode(self, codewriter):
        " pre entry-point setup "
        pass

    @property
    def ref(self):
        return self.name

    def __str__(self):
        return "<%s %r>" % (self.__class__.__name__, self.ref)

class FuncNode(Node):

    def writedecl(self, codewriter):
        " write function forward declarations "
        pass

    def writeimpl(self, codewriter):
        """ write function implementations """ 
        pass
    
class ConstantNode(Node):
    __slots__ = "".split()

    # ______________________________________________________________________
    # entry points from genllvm

    def constantvalue(self):
        """ Returns the constant representation for this node. """
        pass

    def writeglobalconstants(self, codewriter):
        p, c = lltype.parentlink(self.value)
        if p is None:
            codewriter.globalinstance(self.ref, self.constantvalue())
            codewriter.newline()
            codewriter.newline()
        

