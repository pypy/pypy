# Exception Table Migration Plan

## Architecture

**Current PyPy:** runtime linked list of `FrameBlock` objects (`ExceptBlock`, `FinallyBlock`, `SysExcInfoRestorer`) anchored at `frame.lastblock`. The compiler emits `SETUP_FINALLY`/`SETUP_EXCEPT`/`POP_BLOCK` to manage this list. On exception, `unrollstack()` walks the list to find the handler.

**CPython 3.11:** no block stack at all. The exception table `co_exceptiontable` maps bytecode offset ranges to `(handler_offset, stack_depth, lasti_flag)`. Only consulted when an exception actually fires  -- zero overhead on the happy path.

---

## JIT Compatibility

Adopting CPython's model might improve JIT output. Three reasons:

1. `SETUP_FINALLY`/`POP_BLOCK` currently generate virtual `ExceptBlock`/`FinallyBlock` allocations that the JIT eliminates. With the table model those allocations disappear entirely  -- nothing to eliminate.
2. `lastblock` is currently in `PyFrame._virtualizable_`, requiring the JIT to track it at every escape point. It can be removed, simplifying the virtualizable save/restore machinery.
3. Exception dispatch (`unrollstack`) happens outside the traced fast path anyway (it's the guard-failure/blackhole path). Replacing it with a table scan doesn't touch JIT-compiled code at all.

---

## Implementation Phases

| Phase | What | Risk | Status |
|-------|------|------|--------|
| 0 | Add `co_exceptiontable` to `PyCode`, encoder in `assemble.py` | Low | **Done** |
| 1 | `PUSH_EXC_INFO`, `CHECK_EXC_MATCH` opcodes | Medium | **Done** |
| 2 | `handle_operation_error` -> table lookup, update `RERAISE`/`POP_EXCEPT`/`WITH_EXCEPT_START` | High | **Done** (translates) |
| 3 | Compiler: stop emitting `SETUP_FINALLY`/`POP_BLOCK`, emit table entries | High | **Done** (translates) |
| 4 | JIT: remove `lastblock` from `_virtualizable_`, update trace tests | Low | Not started |
| 5 | `fset_f_lineno`: replace `markblocks`/`compatible_block_stack` with table-based validation | Medium | Not started |
| 6 | Remove dead code (`FinallyBlock`, `ExceptBlock`, `SETUP_FINALLY`, etc.) | Low | Not started |

**Critical constraint:** Phases 2 and 3 must be developed in lockstep  -- compiler output must exactly match the new interpreter expectations. Cannot be done incrementally without a feature flag to run both models in parallel.

**Highest-risk point:** `handle_operation_error` rewrite. It has subtle interactions with generators, coroutines, `sys.exc_info()` save/restore, the `hidden_operationerr` mechanism, and JIT blackhole behavior.

**Estimated complexity:** Multi-month project. The compiler changes alone (all `try`/`except`/`finally`/`with`/`except*` patterns in `codegen.py`) are the bulk of the work.

---

## Phases 2+3  -- Implementation Notes

### Table format

Each entry is encoded as a sequence of variable-length integers (CPython-compatible):
`(start, length, target, depth, lasti)` where:
- `start`: byte offset of guarded range start
- `length`: length of guarded range
- `target`: byte offset of handler block
- `depth`: value stack depth at handler entry (before the handler pushes its own values)
- `lasti`: bool  -- whether to preserve `last_instr` at handler entry (used by `RERAISE 1` and `with`)

Entries are stored in bytecode order (non-decreasing `start`). `lookup_exceptiontable` finds the innermost covering entry for a given offset.

### `pycode.py`  -- `lookup_exceptiontable`

Returns a sentinel tuple `(r_uint(0), -1, False)` when no handler is found (`depth == -1` signals not-found). Callers check `depth >= 0`.

### `pyopcode.py`  -- `handle_operation_error`

Marked `@jit.dont_look_inside` because:
- It now contains a `while self.blockstack_non_empty():` loop (to pop legacy `SysExcInfoRestorer`/`FinallyBlock` blocks before jumping to a table-found handler)
- `self` is a virtualizable `PyFrame`, so RPython creates an `__AccessDirect` specialization
- A loopy `access_directly` function that the JIT can't look inside triggers a hard `ValueError` in the JIT codewriter policy
- `handle_operation_error` is only ever called from `except` blocks (not from JIT-traced hot paths), so `dont_look_inside` has no JIT performance cost

New flow: after recording the traceback, try the exception table first. If an entry is found, pop legacy blocks, adjust the value stack to `depth`, push the normalized exception, and return the target offset. If no entry, fall back to `unrollstack()` (old block-stack path, still needed for `with` blocks during the Phase 3->6 transition).

### `RERAISE`

Dual-mode:
- Old path (TOS is `SApplicationException`): block-stack reraise, unchanged.
- New path (TOS is a `BaseException` instance): reconstruct an `OperationError` and call `handle_operation_error(attach_tb=False)`.

### `POP_EXCEPT`

Dual-mode:
- Old path (block stack top is `SysExcInfoRestorer`): pop block and restore `sys.exc_info`.
- New path: pop `w_prev_exc` from value stack, call `ec.set_sys_exc_info3(w_prev_exc)`.

### `WITH_EXCEPT_START`

Dual-mode (detected via `isinstance(TOS, SApplicationException)`):
- Old path: `[..., __exit__, unroller]` on stack  -- extract exception from `unroller.operr`.
- New path: `[..., __exit__, prev_exc, exc]` on stack  -- `exc` is TOS, `__exit__` is at offset 2.

### Translation issues encountered and fixed

| Error | Cause | Fix |
|-------|-------|-----|
| `NoSuchAttrError: 'operr' on W_Root` in `WITH_EXCEPT_START` | `popvalue()` returns `W_Root`; annotator didn't narrow it | Reuse `w_top` (already narrowed by `isinstance` check) |
| `UnionError: SomeTuple vs SomeNone` in `lookup_exceptiontable` | Initial `best = None` vs tuple return | Use sentinel tuple `(r_uint(0), -1, False)`; caller checks `depth >= 0` |
| `AnnotatorError: sorted is not RPython` in `_build_exceptiontable` | `sorted(..., key=lambda)` not supported | Iterate directly (entries are naturally in bytecode order) |
| `ValueError: access_directly on function we don't see handle_operation_error__AccessDirect_None` | New loop in `handle_operation_error` body + virtualizable `self` access | Add `@jit.dont_look_inside` to `handle_operation_error` |

---

## Compiler patterns (Phase 3)

### `try/except` (no name)

```
<table: body -> L_exc, depth=D>
<body>
JUMP_FORWARD L_else
L_exc:  PUSH_EXC_INFO
        LOAD T / CHECK_EXC_MATCH / POP_JUMP_IF_FALSE L_reraise
        POP_TOP
        <handler>
        POP_EXCEPT / JUMP_FORWARD L_end
L_reraise: RERAISE 1
L_else: <orelse>
L_end:
```

### `try/except T as name`

```
<table: body -> L_exc, depth=D>
<body>
JUMP_FORWARD L_else
L_exc:  PUSH_EXC_INFO
        LOAD T / CHECK_EXC_MATCH / POP_JUMP_IF_FALSE L_reraise
        STORE_NAME name                      # [prev_exc]
        <table: hbody -> L_cleanup, depth=D+1>
        <handler body>
        LOAD_CONST None / STORE_NAME name / DELETE_NAME name
        POP_EXCEPT / JUMP_FORWARD L_end
L_cleanup: PUSH_EXC_INFO
           LOAD_CONST None / STORE/DELETE name
           RERAISE 1
L_reraise: RERAISE 1
L_else: <orelse>
L_end:
```

### `try/finally`

```
<table: body -> L_final_exc, depth=D>
<body>
<finally>
JUMP_FORWARD L_end
L_final_exc: PUSH_EXC_INFO
             <finally>
             RERAISE 1
L_end:
```

### `with cm as x`

```
<__enter__ call, push result>
<table: body -> L_exc, depth=D>
<body>
POP_BLOCK / <__exit__(None,None,None)> / POP_TOP
JUMP_FORWARD L_end
L_exc:  PUSH_EXC_INFO
        WITH_EXCEPT_START
        POP_JUMP_IF_TRUE L_suppress
        RERAISE 1
L_suppress: POP_TOP / POP_EXCEPT
L_end:
```

---

## Test status (post Phase 2+3, translated binary)

| Test | Status |
|------|--------|
| test_with | PASS (50/50) |
| test_trace | PASS |
| test_contextlib | PASS |
| test_generators | 2 failures (`test_except_throw_bad_exception`, `coroutine` doctest)  -- pre-existing, not a regression |
| test_exceptions | PASS (PEP 626 lineno failures fixed) |
| test_coroutines | not yet run |
| test_sys_settrace | not yet run (failures expected; blocked on Phase 5) |

---

## Remaining work

### Phase 4  -- JIT cleanup
Remove `lastblock` from `PyFrame._virtualizable_` in `pypy/module/pypyjit/interp_jit.py`. Update JIT trace tests. Low risk, purely additive.

### Phase 5  -- `fset_f_lineno`
The `markblocks`/`compatible_block_stack` machinery in `pycode.py` validates that `f_lineno` assignments land on valid bytecode boundaries. It currently requires a block stack that no longer exists. Replace with exception-table-based validation. This unblocks the 15 `test_sys_settrace` failures.

### Phase 6  -- Dead code removal
Once all tests pass: remove `ExceptBlock`, `FinallyBlock`, `SysExcInfoRestorer`, `SETUP_FINALLY`, `SETUP_EXCEPT`, `POP_BLOCK`, and the dual-mode branches in `RERAISE`/`POP_EXCEPT`/`WITH_EXCEPT_START`/`handle_operation_error`.

### Phase 7  -- Split `last_instr` into display and execution pointers (requires benchmarking)

**Background:** CPython 3.11 maintains two separate pointers:
- `next_instr` (C local): execution pointer, used by `exception_unwind` for table lookup  -- never saved in the frame
- `frame->prev_instr`: display pointer for `f_lasti`/`f_lineno`, overwritten by `RERAISE` to restore the original raise site

Because `exception_unwind` uses the local `next_instr`, RERAISE can freely overwrite `prev_instr` without affecting which handler is found.

**Current PyPy state:** `last_instr` (a frame field in `_virtualizable_`) conflates both roles. `handle_operation_error` reads it for table lookup AND it drives `f_lineno`. The workaround is `_reraise_saved_lasti` (a second frame field), which defers restoring `last_instr` until after the table lookup.

**Goal:** Make `last_instr` a display-only pointer (updated at escapes, written by `RERAISE`), and use the local `next_instr` variable in `dispatch_bytecode` for table lookup. `_reraise_saved_lasti` would be removed.

**Expected benefits:**
- Removes `_reraise_saved_lasti` from every frame (saves 8 bytes per frame)
- Fewer writes to `last_instr` on the hot path -> fewer virtualizable invalidations for the JIT
- Exception table lookup reads a C local (register) instead of a frame field

**Risk:** `last_instr` is read by `bytecode_trace` and `get_last_lineno`  -- decoupling those uses requires care. Must benchmark before and after on pypy-benchmarks to confirm the per-instruction write reduction outweighs refactor complexity. Do not land without benchmark data.

### Next step  -- Phase 4 then Phase 5
Run `test_coroutines` against the translated binary to establish its baseline. Then proceed with Phase 4 (remove `lastblock` from `_virtualizable_`) which is low-risk and self-contained. Follow immediately with Phase 5 (`fset_f_lineno` rewrite) to unblock `test_sys_settrace`. Phase 6 (dead code removal) can then close out the migration.
