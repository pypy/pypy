

class HeapCache(object):
    def __init__(self):
        self.reset()

    def reset(self):
        # contains boxes where the class is already known
        self.known_class_boxes = {}
        # contains frame boxes that are not virtualizables
        self.nonstandard_virtualizables = {}

    def is_class_known(self, box):
        return box in self.known_class_boxes

    def class_now_know(self, box):
        self.known_class_boxes[box] = None

    def is_nonstandard_virtualizable(self, box):
        return box in self.nonstandard_virtualizables

    def nonstandard_virtualizables_now_known(self, box):
        self.nonstandard_virtualizables[box] = None
