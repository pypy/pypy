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

def vertices_reachable_from(root, vertices, edges):
    for event, v in depth_first_search(root, vertices, edges):
        if event == 'start':
            yield v

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
    """Enumerates cycles.  Each cycle is a list of edges.
    This may not give stricly all cycles if they are many intermixed cycles.
    """
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


def find_roots(vertices, edges):
    """Find roots, i.e. a minimal set of vertices such that all other
    vertices are reachable from them."""

    rep = {}    # maps all vertices to a random representing vertex
                # from the same strongly connected component
    for component in strong_components(vertices, edges):
        random_vertex, _ = component.popitem()
        rep[random_vertex] = random_vertex
        for v in component:
            rep[v] = random_vertex

    roots = set(rep.values())
    for v in vertices:
        v1 = rep[v]
        for edge in edges[v]:
            try:
                v2 = rep[edge.target]
                if v1 is not v2:      # cross-component edge: no root is needed
                    roots.remove(v2)  # in the target component
            except KeyError:
                pass

    return roots


def compute_depths(roots, vertices, edges):
    """The 'depth' of a vertex is its minimal distance from any root."""
    depths = {}
    curdepth = 0
    for v in roots:
        depths[v] = 0
    pending = list(roots)
    while pending:
        curdepth += 1
        prev_generation = pending
        pending = []
        for v in prev_generation:
            for edge in edges[v]:
                v2 = edge.target
                if v2 in vertices and v2 not in depths:
                    depths[v2] = curdepth
                    pending.append(v2)
    return depths


def is_acyclic(vertices, edges):
    class CycleFound(Exception):
        pass
    def visit(vertex):
        visiting[vertex] = True
        for edge in edges[vertex]:
            w = edge.target
            if w in visiting:
                raise CycleFound
            if w in unvisited:
                del unvisited[w]
                visit(w)
        del visiting[vertex]
    try:
        unvisited = vertices.copy()
        while unvisited:
            visiting = {}
            root = unvisited.popitem()[0]
            visit(root)
    except CycleFound:
        return False
    else:
        return True


def break_cycles(vertices, edges):
    """Enumerates a reasonably minimal set of edges that must be removed to
    make the graph acyclic."""

    # the approach is as follows: starting from each root, find some set
    # of cycles using a simple depth-first search. Then break the
    # edge that is part of the most cycles.  Repeat.

    remaining_edges = edges.copy()
    progress = True
    roots_finished = set()
    while progress:
        roots = list(find_roots(vertices, remaining_edges))
        #print '%d inital roots' % (len(roots,))
        progress = False
        for root in roots:
            if root in roots_finished:
                continue
            cycles = all_cycles(root, vertices, remaining_edges)
            if not cycles:
                roots_finished.add(root)
                continue
            #print 'from root %r: %d cycles' % (root, len(cycles))
            allcycles = {}
            edge2cycles = {}
            for cycle in cycles:
                allcycles[id(cycle)] = cycle
                for edge in cycle:
                    edge2cycles.setdefault(edge, []).append(id(cycle))
            edge_weights = {}
            for edge, cycle in edge2cycles.iteritems():
                edge_weights[edge] = len(cycle)
            while allcycles:
                max_weight = 0
                max_edge = None
                for edge, weight in edge_weights.iteritems():
                    if weight > max_weight:
                        max_edge = edge
                        max_weight = weight
                if max_edge is None:
                    break
                # kill this edge
                yield max_edge
                progress = True
                # unregister all cycles that have just been broken
                for broken_cycle_id in edge2cycles[max_edge]:
                    broken_cycle = allcycles.pop(broken_cycle_id, ())
                    for edge in broken_cycle:
                        edge_weights[edge] -= 1

                lst = remaining_edges[max_edge.source][:]
                lst.remove(max_edge)
                remaining_edges[max_edge.source] = lst
    assert is_acyclic(vertices, remaining_edges)


def break_cycles_v(vertices, edges):
    """Enumerates a reasonably minimal set of vertices that must be removed to
    make the graph acyclic."""

    # Consider where each cycle should be broken -- we go for the idea
    # that it is often better to break it as far as possible from the
    # cycle's entry point, so that the stack check occurs as late as
    # possible.  For the distance we use a global "depth" computed as
    # the distance from the roots.  The algo below is:
    #  - get a list of cycles
    #  - let maxdepth(cycle) = max(depth(vertex) for vertex in cycle)
    #  - sort the list of cycles by their maxdepth, nearest first
    #  - for each cycle in the list, if the cycle is not broken yet,
    #      remove the vertex with the largest depth
    #  - repeat the whole procedure until no more cycles are found.
    # Ordering the cycles themselves nearest first maximizes the chances
    # that when breaking a nearby cycle - which must be broken in any
    # case - we remove a vertex and break some further cycles by chance.

    v_depths = vertices
    progress = True
    roots_finished = set()
    while progress:
        roots = list(find_roots(v_depths, edges))
        if v_depths is vertices:  # first time only
            v_depths = compute_depths(roots, vertices, edges)
            assert len(v_depths) == len(vertices)  # ...so far.  We remove
            # from v_depths the vertices at which we choose to break cycles
        #print '%d inital roots' % (len(roots,))
        progress = False
        for root in roots:
            if root in roots_finished:
                continue
            cycles = all_cycles(root, v_depths, edges)
            if not cycles:
                roots_finished.add(root)
                continue
            #print 'from root %r: %d cycles' % (root, len(cycles))
            # compute the "depth" of each cycles: how far it goes from any root
            allcycles = []
            for cycle in cycles:
                cycledepth = max([v_depths[edge.source] for edge in cycle])
                allcycles.append((cycledepth, cycle))
            allcycles.sort()
            # consider all cycles starting from the ones with smallest depth
            for _, cycle in allcycles:
                try:
                    choices = [(v_depths[edge.source], edge.source)
                               for edge in cycle]
                except KeyError:
                    pass   # this cycle was already broken
                else:
                    # break this cycle by removing the furthest vertex
                    max_depth, max_vertex = max(choices)
                    del v_depths[max_vertex]
                    yield max_vertex
                    progress = True
    assert is_acyclic(v_depths, edges)


def show_graph(vertices, edges):
    from pypy.translator.tool.graphpage import GraphPage, DotGen
    class MathGraphPage(GraphPage):
        def compute(self):
            dotgen = DotGen('mathgraph')
            names = {}
            for i, v in enumerate(vertices):
                names[v] = 'node%d' % i
            for i, v in enumerate(vertices):
                dotgen.emit_node(names[v], label=str(v))
                for edge in edges[v]:
                    dotgen.emit_edge(names[edge.source], names[edge.target])
            self.source = dotgen.generate(target=None)
    MathGraphPage().display()
