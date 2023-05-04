# Install standard streams for tests that don't call app_main.  Always
# use line buffering, even for tests that capture standard descriptors.

import _io

stdin = _io.open(0, "r", encoding="utf-8",
                closefd=False)
stdin.buffer.raw.name = "<stdin>"

stdout = _io.open(1, "w", encoding="utf-8",
                 buffering=1,
                 closefd=False)
stdout.buffer.raw.name = "<stdout>"

stderr = _io.open(2, "w", encoding="utf-8",
                 errors="backslashreplace",
                 buffering=1,
                 closefd=False)
stderr.buffer.raw.name = "<stderr>"
