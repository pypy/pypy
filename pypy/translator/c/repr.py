
class Repr:
    """Base class: a representation of a constant value of a specific type.
    Each Repr instance knows how to generate C code that defines the
    corresponding value, and which C expression can be used to read it.
    """
    def __init__(self, db, lowleveltype, value):
        self.db = db
        self.lowleveltype = lowleveltype
        self.value = value

    def follow_references(self):
        pass

    def follow_type_references(db, lowleveltype):
        pass
    follow_type_references = staticmethod(follow_type_references)
