optimized_functions = [
    'll_strlen__rpy_stringPtr',
    'll_strconcat__rpy_stringPtr_rpy_stringPtr',   
    'll_stritem_nonneg__rpy_stringPtr_Signed',
    'll_stritem__rpy_stringPtr_Signed',
    'll_streq__rpy_stringPtr_rpy_stringPtr',
    'll_str__IntegerR_SignedConst_Signed',
    'll_chr2str__Char',
    'll_issubclass__object_vtablePtr_object_vtablePtr'  #TODO
]


def optimize_call(statement):
    targetvar, statement = statement.split(' = ', 1)
    funcname, params     = statement.split('(', 1)
    params               = [param.strip() for param in params[:-1].split(',')]

    if funcname == 'll_strlen__rpy_stringPtr':
        return '%s = %s.chars.length' % (targetvar, params[0])

    elif funcname == 'll_strconcat__rpy_stringPtr_rpy_stringPtr':   
        #XXX javascript of ll_strconcat__rpy_stringPtr_rpy_stringPtr actually does not work, FIX IT!
        #    by outcommenting this code end running js/test/test_genllvm.py -k test_simple_chars
        p = '%s.chars' % '.chars + '.join(params)
        return '%s = new Object({hash:0, chars:%s})' % (targetvar, p)
        
    elif funcname == 'll_stritem_nonneg__rpy_stringPtr_Signed':
        return '%s = %s.chars[%s]' % (targetvar, params[0], params[1])

    elif funcname == 'll_stritem__rpy_stringPtr_Signed':
        s, i = params
        return '%s = %s.chars[%s >= 0 ? %s : %s + %s.chars.length]' % (targetvar, s, i, i, i, s)

    elif funcname == 'll_streq__rpy_stringPtr_rpy_stringPtr':
        s0, s1 = params
        return '%s = (%s == %s) || (%s && %s && %s.chars == %s.chars)' %\
                (targetvar, s0,s1, s0,s1, s0,s1)

    elif funcname == 'll_str__IntegerR_SignedConst_Signed':
        return '%s = new Object({hash:0, chars:%s + ""})' % (targetvar, params[0])

    elif funcname == 'll_chr2str__Char':
        return '%s = new Object({hash:0, chars:%s})' % (targetvar, params[0])

    return '%s = %s(%s)' % (targetvar, funcname, ', '.join(params))

def optimize_filesize(filename):
    f = open(filename, "r")
    lines = f.readlines()
    f.close()

    f = open(filename, "w")
    for line in lines:
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        t = line.split('//', 1)
        if len(t) == 2 and '\'"' not in t[0]:
            line = t[0].strip()
            if not line:
                continue
        t = line.split('=', 1)
        if len(t) == 2: 
            t[0] = t[0].strip()
            t[1] = t[1].strip()
            if '\'"' not in t[0]:
                line = '%s=%s' % (t[0], t[1])
        f.write(line)
    f.close()
