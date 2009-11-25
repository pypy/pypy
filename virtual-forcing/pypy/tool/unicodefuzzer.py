import random, sys
random.seed(42)

def make_random_encoded_string(length=10, variance=1):
    s = []
    s.append(random.choice(["\xff\xfe", "\xfe\xff", ""])) # BOM
    for i in range(length + random.randrange(-variance, variance)):
        s.append(chr(random.randrange(256)))
    return "".join(s)

def make_random_unicode(length=10, variance=1):
    s = []
    for i in range(length + random.randrange(-variance, variance)):
        s.append(unichr(random.randrange(sys.maxunicode)))
    return "".join(s)

def check_encode(encoding, s):
    try:
        s.encode(encoding)
    except UnicodeError:
        pass
    s.encode(encoding, "ignore")
    s.encode(encoding, "replace")

def check_decode(encoding, s):
    try:
        s.decode(encoding)
    except UnicodeError:
        pass
    s.decode(encoding, "ignore")
    s.decode(encoding, "replace")

def check_with_length(length):
    try:
        s = make_random_encoded_string(length, 10)
        for encoding in all_encodings:
            check_decode(encoding, s)
    except Exception, e:
        print "decoding:", encoding, repr(s)
    try:
        s = make_random_unicode(length, 10)
        for encoding in all_encodings:
            check_encode(encoding, s)
    except Exception, e:
        print "encoding:", encoding, repr(s)


def main():
    for length in range(0, 1000, 10):
        print length
        for i in range(100):
            check_with_length(length)
    length = 1000
    for length in range(1000, 1000000, 1000):
        print length
        for i in range(100):
            check_with_length(length)

all_encodings = "utf-8 latin1 ascii utf-16 utf-16-be utf-16-le utf-7".split()

if __name__ == '__main__':
    main()

