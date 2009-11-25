import autopath
import pypy.annotation.test.test_annrpython
parent = pypy.annotation.test.test_annrpython.TestAnnotateTestCase


class TestAnnotateAndSimplifyTestCase(parent):
    """Same tests as test_annrpython.TestAnnotateTestCase, but automatically
    running the simplify() method of the annotator after the annotation phase.
    """

    class RPythonAnnotator(parent.RPythonAnnotator):
        def complete(self):
            parent.RPythonAnnotator.complete(self)
            if self.translator is not None:
                self.simplify()
