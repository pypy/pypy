
class GraphPage(object):
    """Base class for the client-side content of one of the 'pages'
    (one graph) sent over to and displayed by the external process.
    """
    def __init__(self, *args):
        self.args = args

    def content(self):
        """Compute the content of the page.
        This doesn't modify the page in place; it returns a new GraphPage.
        """
        if hasattr(self, 'source'):
            return self
        else:
            new = self.__class__()
            new.source = ''  # '''dot source'''
            new.links  = {}  # {'word': 'statusbar text'}
            new.compute(*self.args)   # defined in subclasses
            return new

    def followlink(self, word):
        raise KeyError

    def display(self):
        "Display a graph page."
        import graphclient
        graphclient.display_page(self)

    def display_background(self):
        "Display a graph page in a background thread."
        import graphclient, thread
        thread.start_new_thread(graphclient.display_page, (self,))


class DotFileGraphPage(GraphPage):
    def compute(self, dotfile):
        f = open(dotfile, 'r')
        self.source = f.read()
        f.close()
