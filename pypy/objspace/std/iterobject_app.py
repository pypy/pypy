
class SequenceIterator:
    def __init__(self, it_seq, it_index):
        self.it_seq = it_seq
        self.it_index = it_index
    def __iter__(self):
        return self
    def next(self):
        try:
            item = self.it_seq[self.it_index]
        except IndexError:
            raise StopIteration
        self.it_index += 1
        return item
    # Yes, the implementation is complete, I think

# XXX design a way to have this working and get rid of iterobject.py
# (a very long term design goal, when the interpreter is so fast that
# we can do almost everything in app space -- for now, we just svn rm this!)
