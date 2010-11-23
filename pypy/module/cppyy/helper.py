from pypy.rlib import rstring

def compound(name):
    name = "".join(rstring.split(name, "const")) # poor man's replace
    if name.endswith("]"):                       # array type?
        return "[]"
    i = _find_qualifier_index(name)
    return "".join(name[i:].split(" "))

def array_size(name):
    name = "".join(rstring.split(name, "const")) # poor man's replace
    if name.endswith("]"):                       # array type?
        idx = name.rfind("[")
        if 0 < idx:
            end = len(name)-1                    # len rather than -1 for rpython
            if 0 < end and (idx+1) < end:        # guarantee non-neg for rpython
                return int(name[idx+1:end])
    return -1

def _find_qualifier_index(name):
    i = len(name)
    # search from the back; note len(name) > 0 (so rtyper can use uint)
    for i in range(len(name) - 1, 0, -1):
        c = name[i]
        if c.isalnum() or c == ">" or c == "]":
            break
    return i + 1

def clean_type(name):
    assert name.find("const") == -1
    i = _find_qualifier_index(name)
    name = name[:i].strip(' ')
    if name.endswith("]"):                       # array type?
        idx = name.rfind("[")
        if 0 < idx:
            return name[:idx]
    return name
