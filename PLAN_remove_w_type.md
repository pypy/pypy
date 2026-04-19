# Plan: Remove `w_type` storage from `OperationError` (post-normalization)

Issue: https://github.com/pypy/pypy/issues/5048

## Invariant to exploit

After `normalize_exception()` runs, `w_type` is **always** equal to `space.type(w_value)`.
It is therefore redundant post-normalization. Pre-normalization it is genuinely needed
(to construct `w_value` lazily, and to answer `match()` before the instance exists).

The plan: keep `w_type` while needed, clear it to `None` after normalization, and route all
reads through a new `get_w_type(space)` accessor that derives the type from `_w_value` when
`w_type` is `None`.

## What we are NOT doing

- Removing `_application_traceback`: it is a performance buffer that avoids eager
  normalization during exception propagation across frames. Removing it would force
  the Python exception constructor to run on every frame boundary. See analysis in
  issue discussion.
- Changing the external `oefmt` API: it still takes `w_type` as its first argument.
- Eager normalization: lazy value construction in `OpErrFmt`/`OpErrFmtNoArgs` is preserved.

## Steps

### Step 1 — Fix the 4 `w_type` mutation sites in cpyext (prerequisite)

`pypy/module/cpyext/longobject.py` directly mutates `e.w_type = space.w_OverflowError`
to retag a caught `ValueError` as `OverflowError`. Under the new invariant (type derives
from value) this is incoherent. Replace each with a re-raise:

```python
# before
except OperationError as e:
    if e.match(space, space.w_ValueError):
        e.w_type = space.w_OverflowError
    if e.match(space, space.w_OverflowError) and ...:
        raise oefmt(space.w_OverflowError, "Python int too large ...")
    raise e

# after
except OperationError as e:
    if e.match(space, space.w_ValueError):
        raise oefmt(space.w_OverflowError, "Python int too large ...")
    if e.match(space, space.w_OverflowError) and ...:
        raise oefmt(space.w_OverflowError, "Python int too large ...")
    raise e
```

4 sites, all in `cpyext/longobject.py`.

### Step 2 — Add `get_w_type(space)` accessor to `OperationError`

```python
def get_w_type(self, space):
    w_type = self.w_type          # direct field read — fast
    if w_type is not None:
        return w_type
    return space.type(self._w_value)   # post-normalization path
```

`space.type(w_value)` is effectively `w_value.w_class` — one field read.
The null-check branch is predictable: almost always non-None before normalization.
The JIT can specialize per concrete subtype and eliminate the check for `OpErrFmtNoArgs`.

Lazy subclasses do NOT need to override this — they already set `self.w_type` in `setup()`
and it will be non-None until normalization runs.

### Step 3 — Clear `w_type` at the end of `normalize_exception()`

At the very end of `normalize_exception()`, after updating `self.w_type` and `self._w_value`:

```python
        self.w_type = w_type       # existing (last update before clearing)
        self._w_value = w_value    # existing
        self.w_type = None         # NEW: type is now derivable from _w_value
        return w_value
```

Establishes the invariant: **`w_type is None` iff the exception is fully normalized**.

Side effect to fix: `OpErrFmtNoArgs.async()` currently checks
`self.w_type is space.w_RecursionError`. After Step 3 this check fires only pre-normalization.
Change to `self.get_w_type(space) is space.w_RecursionError`. The JIT specializes the
virtual call to a direct field read for `OpErrFmtNoArgs`.

### Step 4 — Migrate all external `.w_type` reads to `get_w_type(space)`

Approximately 120 direct-access sites. Priority order:

| File | Sites | Notes |
|---|---|---|
| `cpyext/pyerrors.py` | 5 | Production code — borrow-ref semantics, needs space |
| `interpreter/pyopcode.py:1315,1856` | 2 | Inside except handlers — exception always normalized here |
| `interpreter/executioncontext.py:361` | 1 | `sys.exc_info()` tuple construction |
| `interpreter/main.py:111` | 1 | Top-level exception printing |
| `interpreter/reverse_debugging.py:446` | 1 | Debugging only |
| `interpreter/test/test_error.py` | ~10 | Update assertions (see Tests section) |
| `interpreter/test/test_argument.py` | ~8 | Update assertions |
| `module/cpyext/test/` | ~10 | Update assertions |

Note: `set_sys_exc_info3` in `executioncontext.py` already does `w_type = space.type(w_value)`
when constructing an `OperationError` — it already speaks the new dialect.

### Step 5 — (Optional) Rename the field

Once all external reads go through `get_w_type(space)`, rename `w_type` → `_w_type` to
signal it is an internal implementation detail. Update `setup()`, the lazy subclasses, and
`normalize_exception()` accordingly.

## Performance

| Scenario | Before | After |
|---|---|---|
| `match()` pre-normalization (hot) | 1 field read | 1 field read + 1 null-check (predictable, JIT-eliminable) |
| `match()` post-normalization | 1 field read | 2 field reads (`_w_value.w_class`) |
| Lazy `oefmt` path | no eager construction | unchanged |
| GC roots per normalized OperationError | 3 (`w_type`, `_w_value`, `_application_traceback`) | 2 (`w_type=None` freed, `_w_value`, `_application_traceback`) |

## Tests

### Tests that need updating (currently check `.w_type` directly)

- `test_error.py:38` — `assert operr.w_type == "w_type"` → check via `get_w_type` or remove
- `test_error.py:154,162,171` — `e.w_type[0]` (mock space, checks type list)
- `test_argument.py:438,445,453,531,587,655,661` — `excinfo.value.w_type is TypeError`
  → use `excinfo.value.match(space, space.w_TypeError)` or `get_w_type(space)`
- `cpyext/test/test_api.py:22,48` — `operror.w_type is ...` → use `get_w_type(space)`
- `cpyext/test/test_pyerrors.py:57,63,116` — same

### New tests to add (in `test_error.py`)

1. **Invariant: `w_type` is None after normalization**
   ```python
   def test_w_type_cleared_after_normalize(space):
       operr = oefmt(space.w_TypeError, "msg")
       assert operr.w_type is not None          # pre-normalization
       operr.normalize_exception(space)
       assert operr.w_type is None              # cleared
       assert operr.get_w_type(space) is space.w_TypeError  # still accessible
   ```

2. **`get_w_type` works pre-normalization for lazy subclasses**
   ```python
   def test_get_w_type_pre_normalization(space):
       operr = oefmt(space.w_ValueError, "bad %s", "thing")
       assert operr.get_w_type(space) is space.w_ValueError
       assert operr._w_value is None    # still lazy
   ```

3. **`match()` works pre- and post-normalization**
   ```python
   def test_match_pre_and_post_normalization(space):
       operr = oefmt(space.w_TypeError, "msg")
       assert operr.match(space, space.w_TypeError)
       assert not operr.match(space, space.w_ValueError)
       operr.normalize_exception(space)
       assert operr.match(space, space.w_TypeError)   # still works via get_w_type
       assert not operr.match(space, space.w_ValueError)
   ```

4. **Base `OperationError(w_type, w_value)` pre-normalization**
   ```python
   def test_base_operationerror_get_w_type(space):
       operr = OperationError(space.w_RuntimeError, space.w_None)
       assert operr.get_w_type(space) is space.w_RuntimeError
       operr.normalize_exception(space)
       assert operr.w_type is None
       assert operr.get_w_type(space) is space.w_RuntimeError
   ```

These tests pin the new invariant and will catch regressions if normalization accidentally
stops clearing `w_type`.
