
class W_NoneObject:
    delegate_once = {}

    def __eq__(w_self, w_other):
        "Implements 'is'."
        # all w_None wrapped values are equal ('is'-identical)
        return isinstance(w_other, W_NoneObject)
