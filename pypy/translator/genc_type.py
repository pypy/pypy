

class CType_Int:
    ctypetemplate    = 'int %s'
    convert_to_obj   = 'int2obj'
    convert_from_obj = 'obj2int'
    error_return     = '-1'

    def __init__(self, genc):
        pass

    def nameof(self, v, debug=None):
        return '%d' % v
