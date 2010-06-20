import py
from pypy.jit.metainterp import specnode, optimizefindnode
from pypy.tool.pairtype import extendabletype

class __extend__(specnode.NotSpecNode):
    def _dot(self, seen):
        if self in seen:
            return
        seen.add(self)
        yield '%s [label="<Not>"]' % (id(self), )

class __extend__(specnode.ConstantSpecNode):
    def _dot(self, seen):
        if self in seen:
            return
        seen.add(self)
        yield '%s [label="<Const: %s>"]' % (id(self), self.constbox)

class __extend__(specnode.AbstractVirtualStructSpecNode):
    def _dot(self, seen):
        if self in seen:
            return
        seen.add(self)
        yield '%s [label="<%s>"]' % (
                id(self),
                self.__class__.__name__[:-len("SpecNode")])
        for label, node in self.fields:
            yield '%s -> %s [label="%s"]' % (id(self), id(node), label.name)
            for line in node._dot(seen):
                yield line

class __extend__(specnode.VirtualArraySpecNode):
    def _dot(self, seen):
        if self in seen:
            return
        seen.add(self)
        yield '%s [label="<Array: %s>"]' % (
                id(self),
                len(self.items))
        for i, node in enumerate(self.items):
            yield '%s -> %s [label="%s"]' % (id(self), id(node), i)
            for line in node._dot(seen):
                yield line


class __extend__(optimizefindnode.InstanceNode):
    __metaclass__ = extendabletype # evil

    def _dot(self, seen):
        if self in seen:
            return
        seen.add(self)
        if self.knownclsbox:
            name = "Virtual "
            if isinstance(self.knownclsbox.value, int):
                name += str(self.knownclsbox.value)
            else:
                name += str(self.knownclsbox.value.adr.ptr).rpartition("_vtable")[0].rpartition('.')[2]
        elif self.structdescr:
            name = "Struct " + str(self.structdescr)
        elif self.arraydescr:
            name = "Array"
        else:
            name = "Not"
        if self.escaped:
            name = "ESC " + name
        if self.fromstart:
            name = "START " + name
        if self.unique == optimizefindnode.UNIQUE_NO:
            color = "blue"
        else:
            color = "black"

        yield 'orig%s [label="in: [%s]", shape=box, color=%s]' % (
                id(self), name, color)
        yield '%s [label="out: [%s]", shape=box, color=%s]' % (
                id(self), name, color)
        yield 'orig%s -> %s [color=red]' % (id(self), id(self))
        if self.origfields:
            for descr, node in self.origfields.iteritems():
                yield 'orig%s -> orig%s [label="%s"]' % (id(self), id(node), descr.name)
                for line in node._dot(seen):
                    yield line
        if self.curfields:
            for descr, node in self.curfields.iteritems():
                yield '%s -> %s [label="%s"]' % (id(self), id(node), descr.name)
                for line in node._dot(seen):
                    yield line
        if self.origitems:
            for i, node in sorted(self.origitems.iteritems()):
                yield 'orig%s -> orig%s [label="%s"]' % (id(self), id(node), i)
                for line in node._dot(seen):
                    yield line
        if self.curitems:
            for i, node in sorted(self.curitems.iteritems()):
                yield '%s -> %s [label="%s"]' % (id(self), id(node), i)
                for line in node._dot(seen):
                    yield line


def view(*objects):
    from dotviewer import graphclient
    content = ["digraph G{"]
    seen = set()
    for obj in objects:
        content.extend(obj._dot(seen))
    content.append("}")
    p = py.test.ensuretemp("specnodes").join("temp.dot")
    p.write("\n".join(content))
    graphclient.display_dot_file(str(p))

def viewnodes(l1, l2):
    from dotviewer import graphclient
    content = ["digraph G{"]
    seen = set()
    for obj in l1 + l2:
        content.extend(obj._dot(seen))
    for i, (o1, o2) in enumerate(zip(l1, l2)):
        content.append("%s -> %s [color=green]" % (id(o1), i))
        content.append("%s -> orig%s [color=green]" % (i, id(o2)))
    content.append("}")
    p = py.test.ensuretemp("specnodes").join("temp.dot")
    p.write("\n".join(content))
    graphclient.display_dot_file(str(p))
