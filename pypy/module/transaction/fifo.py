
class Fifo(object):
    def __init__(self):
        self.first = None
        self.last = None

    def append(self, newitem):
        newitem.next = None
        if self.last is None:
            self.first = newitem
        else:
            self.last.next = newitem
        self.last = newitem

    def is_empty(self):
        assert (self.first is None) == (self.last is None)
        return self.first is None

    def popleft(self):
        item = self.first
        self.first = item.next
        if self.first is None:
            self.last = None
        return item

    def steal(self, otherfifo):
        if otherfifo.last is not None:
            if self.last is None:
                self.first = otherfifo.first
            else:
                self.last.next = otherfifo.first
            self.last = otherfifo.last
            otherfifo.first = None
            otherfifo.last = None
