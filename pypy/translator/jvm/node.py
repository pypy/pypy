class Node(object):
    def render(self, db, generator):
        unimplemented

class EntryPoint(Node):

    """
    A special node that generates the pypy.Main class which has a static
    main method.  Can be configured with a number of options for internal
    testing (see __init__)
    """

    def __init__(self, graph):
        """
        'graph' --- The initial graph to invoke from main()
        """
        self.graph = graph
        pass

    def render(self, db, gen):
        gen.begin_class('pypy.Main')
        gen.begin_function('main', 'String[]', static=True)

        # XXX --- handle arguments somehow! (will probably need some options)

        # Generate a call to this method
        db.method_for_graph(self.graph).invoke(gen)
        
        gen.end_function()
        gen.end_class()

