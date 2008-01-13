"""
Utilities to manipulate graphs (vertices and edges, not control flow graphs).

Convention:
  'vertices' is a set of vertices (or a dict with vertices as keys);
  'edges' is a dict mapping vertices to a list of edges with its source.
  Note that we can usually use 'edges' as the set of 'vertices' too.
"""

class Edge:
    def __init__(self, source, target):
        self.source = source
        self.target = target
    def __repr__(self):
        return '%r -> %r' % (self.source, self.target)

def make_edge_dict(edge_list):
    "Put a list of edges in the official dict format."
    edges = {}
    for edge in edge_list:
        edges.setdefault(edge.source, []).append(edge)
        edges.setdefault(edge.target, [])
    return edges

def depth_first_search(root, vertices, edges):
    seen = {}
    result = []
    def visit(vertex):
        result.append(('start', vertex))
        seen[vertex] = True
        for edge in edges[vertex]:
            w = edge.target
            if w in vertices and w not in seen:
                visit(w)
        result.append(('stop', vertex))
    visit(root)
    return result

def strong_components(vertices, edges):
    """Enumerates the strongly connected components of a graph.  Each one is
    a set of vertices where any vertex can be reached from any other vertex by
    following the edges.  In a tree, all strongly connected components are
    sets of size 1; larger sets are unions of cycles.
    """
    component_root = {}
    discovery_time = {}
    remaining = vertices.copy()
    stack = []

    for root in vertices:
        if root in remaining:

            for event, v in depth_first_search(root, remaining, edges):
                if event == 'start':
                    del remaining[v]
                    discovery_time[v] = len(discovery_time)
                    component_root[v] = v
                    stack.append(v)

                else:  # event == 'stop'
                    vroot = v
                    for edge in edges[v]:
                        w = edge.target
                        if w in component_root:
                            wroot = component_root[w]
                            if discovery_time[wroot] < discovery_time[vroot]:
                                vroot = wroot
                    if vroot == v:
                        component = {}
                        while True:
                            w = stack.pop()
                            del component_root[w]
                            component[w] = True
                            if w == v:
                                break
                        yield component
                    else:
                        component_root[v] = vroot

def all_cycles(root, vertices, edges):
    """Enumerates cycles.  Each cycle is a list of edges."""
    stackpos = {}
    edgestack = []
    result = []
    def visit(v):
        if v not in stackpos:
            stackpos[v] = len(edgestack)
            for edge in edges[v]:
                if edge.target in vertices:
                    edgestack.append(edge)
                    visit(edge.target)
                    edgestack.pop()
            stackpos[v] = None
        else:
            if stackpos[v] is not None:   # back-edge
                result.append(edgestack[stackpos[v]:])
    visit(root)
    return result        

def break_cycles(vertices, edges):
    """Enumerates a reasonably minimal set of edges that must be removed to
    make the graph acyclic."""
    # the approach is as follows: for each strongly connected component, find
    # all cycles (which takens exponential time, potentially). Then break the
    # edges that are part of the most cycles, until all cycles in that
    # component are broken.
    for component in strong_components(vertices, edges):
        #print '-->', ''.join(component)
        random_vertex = component.iterkeys().next()
        cycles = all_cycles(random_vertex, component, edges)
        if not cycles:
            continue
        allcycles = dict.fromkeys([id(cycle) for cycle in cycles])
        edge2cycles = {}
        edge_weights = {}
        for cycle in cycles:
            #print '\tcycle:', [e.source+e.target for e in cycle]
            for edge in cycle:
                edge2cycles.setdefault(edge, []).append(cycle)
                edge_weights[edge] = edge_weights.get(edge, 0) + 1
        while allcycles:
            max_weight = 0
            max_edge = None
            for edge, weight in edge_weights.iteritems():
                if weight >= max_weight:
                    max_edge = edge
                    max_weight = weight
            broken_cycles = edge2cycles[max_edge]
            assert max_edge is not None
            # kill this edge
            yield max_edge
            for broken_cycle in broken_cycles:
                try:
                    del allcycles[id(broken_cycle)]
                except KeyError:
                    pass
                else:
                    for edge in broken_cycle:
                        edge_weights[edge] -= 1
                        if edge_weights[edge] == 0:
                            del edge_weights[edge]
