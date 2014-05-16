""" AnnotatedValue """

class AnnotatedValue(object):
    def __init__(self, value, annotation):
        self.value = value
        self.ann = annotation

    def __repr__(self):
        return "AnnotatedValue(%s, %r)" % (self.value, self.ann)
