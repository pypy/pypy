"""

Turning function dependencies into linear order
-----------------------------------------------

The purpose of this module is to calculate a good linear
ordering of functions, according to call transition
statistics.

Every node has some connections to other nodes, expressed
in terms of transition frequencies. As a starting point,
one could assign every node its own dimension. All transitions
would therefore be orthogonal to each other. The resulting
vector space would be quite huge.

Instead, we use a different approach:

For a node having t transitions, we order the transitions
by decreasing frequencies. The initial position of each
node is this t-dimensional vector.

The distance between two nodes along a transition is the
Euclidean distance of the intersecion of the nodes dimensions.
The transition frequencies define a weight for each transition.
The weighted distance between two nodes
"""

from math import sqrt
import random


def zipextend(v1, v2):
    adjust = len(v2) - len(v1)
    if adjust:
        if adjust > 0:
            v1 += [0.0] * adjust
        else:
            v2 = v2[:] + [0.0] * -adjust
    return zip(v1, v2)


class Vector:
    # a really dumb little helper class

    def __init__(self, seq=None):
        self.coords = list(seq or [])

    def __inplace_add__(self, other):
        self.coords = [p + q for p, q in zipextend(self.coords, other.coords)]

    def __inplace_sub__(self, other):
        self.coords = [p - q for p, q in zipextend(self.coords, other.coords)]

    def __inplace_mul__(self, scalar):
        if isinstance(scalar, Vector):
            # dot product. zip is correct here, zero cancels.
            other = scalar
            self.coords = [p * q for p, q in zip(self.coords, other.coords)]
        else:
            # scalar product
            self.coords = [p * scalar for p in self.coords]

    def __inplace_div__(self, scalar):
        self.coords = [p / scalar for p in self.coords]

    def __add__(self, other):
        vec = Vector(self.coords)
        vec.__inplace_add__(other)
        return vec

    def __sub__(self, other):
        vec = Vector(self.coords)
        vec.__inplace_sub__(other)
        return vec

    def __mul__(self, scalar):
        vec = Vector(self.coords)
        vec.__inplace_mul__(scalar)
        return vec

    def __div__(self, scalar):
        vec = Vector(self.coords)
        vec.__inplace_div__(scalar)
        return vec

    def __neg__(self):
        return Vector([-k for k in self.coords])

    def norm2(self):
        if len(self.coords) == 1:
            return abs(self.coords[0])
        return sqrt(sum([k * k for k in self.coords]))

    def getdim(self):
        return len(self.coords)

    # access to coordinates
    def __getitem__(self, idx):
        return self.coords[idx]

    def __setitem__(self, idx, value):
        self.coords[idx] = value

    def __iter__(self):
        return iter(self.coords)

    def __repr__(self):
        return 'Vector(%r)' % self.coords

class SpaceNode:
    def __init__(self, node):
        self.func = node.func
        self.name = node.name

    def setup(self, relations, weights, initpos):
        self.relations = relations
        self.weights = weights
        self.position = initpos

    def distance(self, other):
        # using the nice property of zip to give the minimum length
        return (other.position - self.position).norm2()

    def scale(self, factor):
        self.position *= factor

    def shift(self, delta):
        self.position += delta

    def shiftx(self, deltax):
        self.position[0] += deltax

    def lonelyness(self):
        # get the square norm of weighted distances
        lonely = []
        for weight, relative in zip(self.weights, self.relations):
            lonely.append(weight * self.distance(relative))
        return Vector(lonely).norm2()

    def forcevector(self):
        # weighted implementation of the "rubber2" algorithm,
        # from "PolyTop", (C) Christian Tismer / Gerhard G. Thomas  1992
        vec = Vector()
        for w, rel in zip(self.weights, self.relations):
            tmp = rel.position - self.position
            lng = tmp.norm2()
            tmp *= w * lng
            vec += tmp
            # this is a little faster than
            # vec += (rel.position - self.position) * w * self.distance(rel)
        return vec


class SpaceGraph:
    random = random.Random(42).random

    def __init__(self, simgraph):
        self.nodes = []
        self.addgraph(simgraph)
        self.lastdim = 0 # calculated by normalize
        self.subgraphs = []

    def addgraph(self, simgraph):
        mapping = {}
        for simnode in simgraph.nodes:
            mapping[simnode] = SpaceNode(simnode)
        i = len(self.nodes)
        self.nodes += [mapping[simnode] for simnode in simgraph.nodes]
        for simnode in simgraph.nodes:
            relations, weights = simnode.get_relations()
            relations = [mapping[rel] for rel in relations]
            node = mapping[simnode]
            # extreme simplification:
            # use just one dimension
            # scamble as much as possible to avoid
            # starting in a local minimum
            #node.setup(relations, weights, Vector([i]))
            node.setup(relations, weights, Vector([self.random()]))
            i += 1
        self.subgraphs = []

    def xminmax(self, nodes=None):
        nodes = nodes or self.nodes
        xaxis = [node.position[0] for node in nodes]
        xmin = min(xaxis)
        xmax = max(xaxis)
        return float(xmin), float(xmax)

    def compute_subgraphs(self):
        nodes = {}
        for node in self.nodes:
            nodes[node] = node
        self.subgraphs = []
        while nodes:
            for node in nodes:
                break
            todo = [node]
            del nodes[node]
            for node in todo:
                for rel in node.relations:
                    if rel in nodes:
                        del nodes[rel]
                        todo.append(rel)
            self.subgraphs.append(todo)

    def normalize(self):
        # identify disjoint subgraphs.
        # for every subgraph:
        #   move the graph center to zero
        #   scale the graph to make the x-axis as long as the number of nodes.
        # shift all graphs to be in disjoint intervals on the x-axis.
        if not self.subgraphs:
            self.compute_subgraphs()
        def distort(nodes):
            # stretch collapsed x-axis
            for i, node in enumerate(nodes):
                node.position[0] = i
            return nodes
        def norm_subgraph(nodes, start):
            # normalize a subgraph, return the dimensionality as side effect
            xmin, xmax = self.xminmax(nodes)
            xwidth = xmax - xmin
            if not xwidth: # degenerated
                return norm_subgraph(distort(nodes))
            factor = (len(nodes) - 1) / xwidth
            mean = Vector()
            for node in nodes:
                mean += node.position
            mean /= len(nodes)
            shift = -mean
            dim = shift.getdim()
            for node in nodes:
                node.shift(shift)
                node.scale(factor)
            shiftx = start - (xmin + shift[0]) * factor
            for node in nodes:
                node.shiftx(shiftx)
            return dim

        start = 0.0
        dim = 0
        for nodes in self.subgraphs:
            dim = max(dim, norm_subgraph(nodes, start))
            start += len(nodes)
        self.lastdim = dim

    def do_correction(self, korr=0.13):
        forcevecs = [node.forcevector() for node in self.nodes]
        corrx = [vec[0] for vec in forcevecs]
        maxcorr = abs(max(corrx))
        xmin, xmax = self.xminmax()
        xwidth = xmax - xmin
        scale = xwidth / maxcorr
        scale = scale * korr
        for node, forcevec in zip(self.nodes, forcevecs):
            corrvec = forcevec * scale
            node.shift(corrvec)

    def squeeze_dim(self):
        scale = []
        ndim = self.lastdim
        for i in range(ndim):
            scale.append( 1.01 ** -i )
        scale = Vector(scale)
        for node in self.nodes:
            node.scale(scale)

    def lonelyness2(self):
        # square norm of lonelynesses
        lonely = []
        for node in self.nodes:
            lonely.append(node.lonelyness())
        return Vector(lonely).norm2()

    def lonelyness(self):
        # square norm of lonelynesses
        lonely = 0.0
        for node in self.nodes:
            lonely += node.lonelyness()
        return lonely / len(self.nodes)

    def order(self):
        sorter = [(node.position[0], node) for node in self.nodes]
        sorter.sort()
        return [node for x, node in sorter]

    def display(self):
        for node in self.order():
            print node.name, node.lonelyness(), node.position

if __name__ == '__main__':
    from pypy.translator.locality.simulation import SimGraph
    def test():
        def a(): b()
        def b(): c()
        def c(): d()
        def d(): e()
        def e(): f()
        def f(): a()
        sim = DemoSim([a, b, c, d, e, f])
        sim.sim_all(0.9, 50)
        return sim
    g = SpaceGraph(test())
    g.addgraph(test())
    g.addgraph(test())
