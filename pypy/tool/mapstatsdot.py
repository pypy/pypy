#! /usr/bin/env python
import sys
sys.setrecursionlimit(100000)

class Getattrwrap(object):
    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, name):
        try:
            return self.obj[name]
        except KeyError:
            return None

    def __repr__(self):
        return "<%s>" % (self.obj, )


class Map(object):
    allmaps = {}
    instances = 0

    def __init__(self, typ, id):
        self.type = typ
        self.id = id
        self.allmaps[id] = self

    @staticmethod
    def make(content):
        typ = content.type
        cls = Map
        if typ == 'PlainAttribute':
            cls = Attribute
        elif "Terminator" in typ:
            cls = Terminator
        else:
            import pdb; pdb.set_trace()
        return cls(typ, content.id)

    def fill(self, content):
        self.raw = content
        self.type = content.type
        self.direct_instances = content.instances
        self.instances += content.instances

        transitions = content.transitions
        d = {}
        if transitions:
            for id, count in transitions.iteritems():
                map = Map.getmap(id)
                map.instances += count
                d[map] = count
        self.transitions = d

    @staticmethod
    def getmap(id):
        return Map.allmaps[id]

    def dot(self, output, seen):
        if self in seen:
            return
        seen.add(self)
        if hasattr(self, 'back'):
            if self not in self.back.transitions:
                output.edge(self.back.id, self.id, dir="back")
            self.back.dot(output, seen)
        if not self.instances:
            return
        node = output.node(self.id, label=self.getlabel(),
                           shape="box", labeljust="r",
                           fillcolor=self.getfillcolor())
        for next, count in self.transitions.iteritems():
            next.dot(output, seen)
            args = {}
            if getattr(next, 'back', None) is not self:
                args = dict(style="dotted")
            output.edge(self.id, next.id, label=str(count), **args)
        return node

    def getfillcolor(self):
        if len(self.transitions) > 1:
            return "red"
        return "white"


class Terminator(Map):
    def __repr__(self):
        return "Terminator(%s)" % (self.w_cls)
    def fill(self, content):
        Map.fill(self, content)
        self.w_cls = content.w_cls
        self.w_cls_module = content.w_cls_module

    def getlabel(self):
        if self.w_cls_module is not None:
            return self.w_cls + "\\l" + self.w_cls_module
        return self.w_cls

    def get_chain(self):
        return [self]


class Attribute(Map):
    def fill(self, content):
        Map.fill(self, content)
        self.back = Map.getmap(content.back)
        self.name = content.name
        self.nametype = content.index
        self.ever_mutated = content.ever_mutated
        self.can_contain_mutable_cell = content.can_contain_mutable_cell
        self.hprof_status = content._hprof_status
        self.constant = False
        if self.hprof_status == "i":
            self.constant = True
        if self.hprof_status == "o":
            self.constant = True
        self.constant_class = content._hprof_const_cls
        self.number_unnecessary_writes = content.number_unnecessary_writes

        writes = content.writes
        d = {}
        if writes:
            for tup, count in writes.iteritems():
                key, index, cls = tup.strip('()').split(', ')
                if key.startswith(('"', "'")):
                    key = eval(key)
                assert key == self.name
                assert int(index) == self.nametype
                d[cls] = count
        self.writes = d

        reads = content.reads
        count = 0
        if reads:
            assert len(reads) == 1
            for tup, count in reads.iteritems():
                key, index = tup.strip('()').split(', ')
                if key.startswith(('"', "'")):
                    key = eval(key)
                assert key == self.name
                assert int(index) == self.nametype
        self.reads = count

    def get_chain(self):
        l = []
        while isinstance(self, Attribute):
            l.append((self.name, self.nametype))
            self = self.back
        l.reverse()
        return self.get_chain() + l

    def getlabel(self):
        if self.nametype == 0:
            name = self.name
        else:
            name = self.name + " " + str(self.nametype)
        if self.hprof_status == "i":
            name += " (constant int)"
        if self.hprof_status == "o":
            name += " (constant obj)"
        label = [name]
        label.append("reads: %s" % self.reads)
        label.append("writes:")
        for write, count in self.writes.items():
            label.append("    %s: %s" % (write, count))
        if self.number_unnecessary_writes and self.constant:
            assert len(self.writes) <= 1
            label[-1] += " (%s unnecessary)" % (self.number_unnecessary_writes, )
        if not self.ever_mutated:
            label.append('immutable')
        if self.can_contain_mutable_cell and not self.constant_class:
            label.append('may be a cell')
        if self.constant_class:
            label.append('constant class: ' + self.constant_class)
        return "\\l".join(label)

    def getfillcolor(self):
        if len(self.transitions) > 1:
            return "red"
        if len(self.writes) > 1: # more than one type
            return "yellow"
        if self.constant:
            return "green"
        if self.constant_class:
            return "greenyellow"
        return "white"

def dot(allmaps):
    import graphviz
    output = graphviz.Digraph()
    seen = set()
    #allmaps = [map for map in allmaps if map.instances and map.getfillcolor() != "white"]
    allmaps.sort(key=lambda map: getattr(map, "instances", 0))
    allmaps.reverse()
    for map in allmaps:
        map.dot(output, seen)
    print output.source


def main():
    input = eval(file(sys.argv[1]).read())
    input = [Getattrwrap(obj) for obj in input]
    allmaps = []
    for mp in input:
        allmaps.append(Map.make(mp))
    for content in input:
        mp = Map.getmap(content.id)
        mp.fill(content)
    totalreads = 0
    goodreads = 0
    totalwrites = 0
    goodwrites = 0
    totalattrs = 0
    goodattrs = 0
    unnecessary = 0

    seen_sorted_chains = set()
    duplicate_orders = 0
    duplicate_order_reads = 0
    all_instances = 0

    for mp in allmaps:
        chain = mp.get_chain()
        chain.sort()
        if tuple(chain) in seen_sorted_chains:
            duplicate_orders += 1
            duplicate_order_reads += mp.reads
            print >> sys.stderr, chain, mp.instances
        else:
            seen_sorted_chains.add(tuple(chain))

        if not isinstance(mp, Attribute):
            continue
        totalwrites += sum(mp.writes.values())
        totalreads += mp.reads
        totalattrs += 1
        if len(mp.writes) == 1:
            goodwrites += sum(mp.writes.values())
            goodreads += mp.reads
            goodattrs += 1
        if mp.constant:
            unnecessary += mp.number_unnecessary_writes
    with file("out.csv", "a") as f:
        print >> f, ", ".join(map(str, [sys.argv[1], totalreads, goodreads, totalwrites, goodwrites, unnecessary, totalattrs, goodattrs]))
    print >> sys.stderr, "reads:", totalreads, goodreads, float(goodreads) / totalreads
    print >> sys.stderr, "writes:", totalwrites, goodwrites, float(goodwrites) / totalwrites
    print >> sys.stderr, "unnecessary writes:", unnecessary, totalwrites, float(unnecessary) / totalwrites
    print >> sys.stderr, "wrongly ordered:", duplicate_orders, totalattrs, float(duplicate_orders) / totalattrs
    print >> sys.stderr, "wrongly ordered reads:", duplicate_order_reads, totalreads, float(duplicate_order_reads) / totalreads
    print >> sys.stderr, "attrs:", totalattrs, goodattrs, float(goodattrs) / totalattrs
    print >> sys.stderr, "reads / writes", float(totalreads) / totalwrites

    dot(allmaps)

if __name__ == '__main__':
    main()
