"""
Utilities to manipulate graphs (vertices and edges, not control flow graphs).
"""

class Edge:
    def __init__(self, source, target):
        self.source = source
        self.target = target

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
    a set of vertices where any node can be reached from any other vertex by
    following the edges.  'edges' is a dict {vertex: [edges]})"""

    component_root = {}
    discovery_time = {}
    stack = []

    for root in vertices:
        if root not in discovery_time:

            for event, v in depth_first_search(root, vertices, edges):
                if event == 'start':
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
                    if vroot is v:
                        component = {}
                        while True:
                            w = stack.pop()
                            del component_root[w]
                            component[w] = True
                            if w is v:
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
    graphs = [(vertices, edges)]
    for vertices, edges in graphs:
        #print ''.join(vertices),
        #print [e.source+e.target for l in edges.values() for e in l]
        for component in strong_components(vertices, edges):
            #print '-->', ''.join(component)
            edge_weights = {}
            random_vertex = component.iterkeys().next()
            for cycle in all_cycles(random_vertex, vertices, edges):
                #print '\tcycle:', [e.source+e.target for e in cycle]
                for edge in cycle:
                    edge_weights[edge] = edge_weights.get(edge, 0) + 1
            if edge_weights:
                max_weight = max(edge_weights.values())
                for edge, weight in edge_weights.iteritems():
                    if weight == max_weight:
                        break
                # kill this edge
                yield edge
                new_edges = edges.copy()
                new_edges[edge.source] = [e for e in new_edges[edge.source]
                                            if e is not edge]
                graphs.append((component, new_edges))
