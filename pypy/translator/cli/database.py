try:
    set
except NameError:
    from sets import Set as set


class LowLevelDatabase(object):
    def __init__(self):
        self.classes = set()
        self.pending_graphs = []
        self.functions = {} # graph --> function_name
        self.methods = {} # graph --> method_name

    def record_function(self, graph, name):
        self.functions[graph] = name

    def function_name(self, graph):
        return self.functions.get(graph, None)
