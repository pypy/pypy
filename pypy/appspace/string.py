def maketrans(origin, image):
    if len(origin) != len(image):
        raise ValueError("maketrans arguments must have same length")
    L = [chr(i) for i in range(256)]
    for i in range(len(origin)):
        L[ord(origin[i])] = image[i]

    tbl = ''.join(L)
    return tbl