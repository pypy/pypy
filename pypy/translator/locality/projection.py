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

from pypy.translator.locality.simulation import DemoNode, DemoSim
from math import sqrt

class SpaceNode:
    def __init__(self, node):
        self.func = node.func
        self.name = node.name

    def setup(self, relations, weights):
        self.relations = relations
        self.weights = weights
        self.position = weights[:] # just anything to start with

    def distance(self, other):
        # using the nice property of zip to give the minimum length
        dist = 0.0
        for x1, x2 in zip(self.position, other.position):
            d = x2 - x1
            dist += d * d
        return sqrt(dist)

    def lonelyness(self):
        # get the sum of weighted distances
        lonely = 0.0
        for weight, relative in zip(self.weights, self.relations):
            lonely += weight * self.distance(relative)
        return lonely

    def corrvector(self):
        pass # XXX continue here

class SpaceGraph:
    def __init__(self, simgraph):
        mapping = {}
        for simnode in simgraph.nodes:
            mapping[simnode] = SpaceNode(simnode)
        self.nodes = [mapping[simnode] for simnode in simgraph.nodes]
        for simnode in simgraph.nodes:
            relations, weights = simnode.get_relations()
            relations = [mapping[rel] for rel in relations]
            node = mapping[simnode]
            node.setup(relations, weights)

if __name__ == '__main__':
    from pypy.translator.locality.simulation import test
    g = SpaceGraph(test())
