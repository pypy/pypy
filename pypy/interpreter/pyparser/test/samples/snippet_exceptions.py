try:
    a
    b
except:
    pass

try:
    a
    b
except NameError:
    pass

try:
    a
    b
except NameError, err:
    pass

try:
    a
    b
except (NameError, ValueError):
    pass


try:
    a
    b
except (NameError, ValueError), err:
    pass

try:
    a
except NameError, err:
    pass
except ValueError, err:
    pass

try:
    a
except NameError, err:
    pass
except ValueError, err:
    pass
else:
    pass

try:
    a
finally:
    b



