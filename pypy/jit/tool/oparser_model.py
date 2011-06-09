class Boxes(object):
    pass

def get_real_model():
    class LoopModel(object):
        from pypy.jit.metainterp.history import TreeLoop, LoopToken
        from pypy.jit.metainterp.history import Box, BoxInt, BoxFloat
        from pypy.jit.metainterp.history import ConstInt, ConstObj, ConstPtr, ConstFloat
        from pypy.jit.metainterp.typesystem import llhelper

    return LoopModel

def get_mock_model():
    class LoopModel(object):

        class TreeLoop(object):
            def __init__(self, name):
                self.name = name

        class LoopToken(object):
            I_am_a_descr = True

        class Box(object):
            _counter = 0
            type = 'b'

            def __init__(self, value=0):
                self.value = value

            def __repr__(self):
                result = str(self)
                result += '(%s)' % self.value
                return result

            def __str__(self):
                if not hasattr(self, '_str'):
                    self._str = '%s%d' % (self.type, Box._counter)
                    Box._counter += 1
                return self._str

        class BoxInt(Box):
            type = 'i'

        class BoxFloat(Box):
            type = 'f'

        class BoxRef(Box):
            type = 'p'

        class Const(object):
            def __init__(self, value=None):
                self.value = value

        class ConstInt(Const):
            pass

        class ConstPtr(Const):
            pass

        class ConstFloat(Const):
            pass

        class llhelper(object):
            pass

    LoopModel.llhelper.BoxRef = LoopModel.BoxRef

    return LoopModel


def get_model(use_mock):
    if use_mock:
        model = get_mock_model()
    else:
        model = get_real_model()

    class ExtendedTreeLoop(model.TreeLoop):

        def getboxes(self):
            def opboxes(operations):
                for op in operations:
                    yield op.result
                    for box in op.getarglist():
                        yield box
            def allboxes():
                for box in self.inputargs:
                    yield box
                for box in opboxes(self.operations):
                    yield box

            boxes = Boxes()
            for box in allboxes():
                if isinstance(box, model.Box):
                    name = str(box)
                    setattr(boxes, name, box)
            return boxes

        def setvalues(self, **kwds):
            boxes = self.getboxes()
            for name, value in kwds.iteritems():
                getattr(boxes, name).value = value

    model.ExtendedTreeLoop = ExtendedTreeLoop
    return model
