
class Stack:
    """A very simple stack interface
    (not very useful in Python)
    """

    def __init__(self, max_size = 10):
        self.max_size = max_size
        self.elements = []

    def _pre_pop(self):
        return not self.is_empty()
    def _post_pop(self, old, ret):
        return ret == old.top() and \
               self.size() == old.size() - 1
    def pop(self):
        return self.elements.pop()


    def _pre_push(self, obj):
        return obj is not None and not self.is_full()
    def _post_push(self, old, ret, obj):
        return not self.is_empty() and (self.top() == obj)
    def push(self, obj):
        self.elements.append(obj)


    def top(self):
        """Returns the top element of the stack
        """
        return self.elements[-1]
    
    def is_empty(self):
        """Tells whether or not the stack is empty
        """
        return not bool(self.elements)


    def is_full(self):
        """Tells whether or not the stack is full
        """
        return len(self.elements) == self.max_size
    
    def size(self):
        """Returns the current size of the stack
        """
        return len(self.elements)

    def __str__(self):
        return "elements = %s, max_size = %s" % (self.elements, self.max_size)
