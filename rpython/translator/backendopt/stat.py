from rpython.translator.simplify import get_graph
from hashlib import md5
from collections import defaultdict

def find_reachable_graphs(graph, translator, ignore_stack_checks=False):
    seen_graphs = set()
    stack = [graph]
    while stack:
        graph = stack.pop()
        if graph in seen_graphs:
            continue
        seen_graphs.add(graph)
        yield graph
        for block, op in graph.iterblockops():
            if op.opname == "direct_call":
                called_graph = get_graph(op.args[0], translator)
                if called_graph is not None and ignore_stack_checks:
                    if called_graph.name.startswith('ll_stack_check'):
                        continue
                if called_graph is not None:
                    stack.append(called_graph)
            elif op.opname == "indirect_call":
                called_graphs = op.args[-1].value
                if called_graphs is not None:
                    stack.extend(called_graphs)


def get_statistics(graph, translator, save_per_graph_details=None, ignore_stack_checks=False):
    num_graphs = 0
    num_blocks = 0
    num_ops = 0
    num_mallocs = 0
    num_memory = 0
    per_graph = {}
    for graph in find_reachable_graphs(graph, translator, ignore_stack_checks):
        num_graphs += 1
        old_num_blocks = num_blocks
        old_num_ops = num_ops
        old_num_mallocs = num_mallocs
        old_num_memory = num_memory
        for block in graph.iterblocks():
            num_blocks += 1
            for op in block.operations:
                if op.opname.startswith("malloc"):
                    num_mallocs += 1
                elif op.opname.startswith(("get", "set")):
                    num_memory += 1
                num_ops += 1
        per_graph[graph] = (num_blocks-old_num_blocks, num_ops-old_num_ops, num_mallocs-old_num_mallocs, num_memory-old_num_memory)
    if save_per_graph_details:
        details = []
        for graph, (nblocks, nops, nmallocs, nmemory) in per_graph.iteritems():
            try:
                code = graph.func.func_code.co_code
            except AttributeError:
                code = "None"
            hash = md5(code).hexdigest()
            details.append((hash, graph.name, nblocks, nops, nmallocs, nmemory))
        details.sort()
        f = open(save_per_graph_details, "w")
        try:
            for hash, name, nblocks, nops, nmallocs, nmemory in details:
                print >>f, hash, name, nblocks, nops, nmallocs, nmemory
        finally:
            f.close()
    return num_graphs, num_blocks, num_ops, num_mallocs, num_memory

def print_statistics(graph, translator, save_per_graph_details=None, ignore_stack_checks=False):
    num_graphs, num_blocks, num_ops, num_mallocs, num_memory = get_statistics(
            graph, translator, save_per_graph_details,
            ignore_stack_checks=ignore_stack_checks)
    print ("Statistics:\nnumber of graphs %s\n"
           "number of blocks %s\n"
           "number of operations %s\n"
           "number of mallocs %s\n"
           "number of memory operations %s\n"
           ) % (num_graphs, num_blocks, num_ops, num_mallocs, num_memory)
    calls = defaultdict(int)
    opnames = defaultdict(int)
    for graph in find_reachable_graphs(graph, translator):
        for block, op in graph.iterblockops():
            opnames[op.opname] += 1
            if op.opname == "direct_call":
                called_graph = get_graph(op.args[0], translator)
                if called_graph is not None and ignore_stack_checks:
                    if called_graph.name.startswith('ll_stack_check'):
                        continue
                if called_graph is not None:
                    calls[called_graph] += 1
            elif op.opname == "indirect_call":
                called_graphs = op.args[-1].value
                if called_graphs is not None:
                    for called_graph in called_graphs:
                        calls[called_graph] += 1
    for num, name in sorted((num, name) for (name, num) in opnames.iteritems()):
        print name, num
    print
    for num, graph in sorted((num, graph) for (graph, num) in calls.iteritems())[-100:]:
        print graph.name, num
