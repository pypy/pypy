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
| 2 | `handle_operation_error` -> table lookup, update `RERAISE`/`POP_EXCEPT`/`WITH_EXCEPT_START` | High | **Done** |
| 3 | Compiler: stop emitting `SETUP_FINALLY`/`POP_BLOCK`, emit table entries | High | **Done** |
| 4 | JIT: remove `lastblock` from `_virtualizable_`, update trace tests | Low | **Done** |
| 5 | `fset_f_lineno`: replace `markblocks`/`compatible_block_stack` with table-based validation | Medium | **Done** |
| 6 | Remove dead code (`FinallyBlock`, `ExceptBlock`, `SETUP_FINALLY`, etc.) | Low | **Done** |
| 7 | Compiler: replace scattered `emit_exception_table_entry` calls with single linear scan | Medium | **Done** |
| 8 | Make `SETUP_FINALLY`/`SETUP_CLEANUP`/`POP_BLOCK` pseudo-instructions (size 0, not encoded) | Medium | **Done** |
| 9 | Remove `SETUP_FINALLY`/`SETUP_CLEANUP`/`POP_BLOCK` from dispatch; replace with private constants | Medium | **Done** |
| 10 | Fix `with`-handler exception table coverage gap (handler blocks fall outside enclosing scope ranges) | Medium | Not started |
| 11 | Make `SETUP_WITH`/`SETUP_ASYNC_WITH` pseudo-instructions; emit `__enter__` as plain call from compiler | Medium | Not started |
| 12 | Split `last_instr` into display/execution pointers (requires benchmarking) | Medium | Not started |
| 13 | Flow-graph-based exception table to fix `duplicate_exits_without_lineno` gap | Medium | Not started |

**Critical constraint:** Phases 2 and 3 must be developed in lockstep  -- compiler output must exactly match the new interpreter expectations. Cannot be done incrementally without a feature flag to run both models in parallel.

**Highest-risk point:** `handle_operation_error` rewrite. It has subtle interactions with generators, coroutines, `sys.exc_info()` save/restore, the `hidden_operationerr` mechanism, and JIT blackhole behavior.

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

## Remaining work

### Phase 10  -- Fix `with`-handler exception table coverage gap

**Background:** In the Phase 7 linear scan, `with`-handler blocks (containing
`PUSH_EXC_INFO` / `WITH_EXCEPT_START` / ...) are placed in the flat instruction stream
after the `_POP_BLOCK` that closes the enclosing `try` or `with` scope.  By that point the
linear scan has already popped the enclosing handler, so the handler block itself has no
exception table entry.  When `WITH_EXCEPT_START` raises (e.g. because `__exit__` raises),
the exception escapes the enclosing `try/except` or outer `with` instead of being caught
by it.

**Symptoms:** `test_shutil.TestCopyFile.test_w_dest_close_fails` / `test_w_source_close_fails` --
`copyfileobj` raises AttributeError (because `Faux.__enter__` returns None), the inner
`with`'s `WITH_EXCEPT_START` calls `destfile.__exit__` which raises OSError, but OSError
escapes the outer `with open(src)` instead of being suppressed by `srcfile.__exit__`.

**Fix:** Add `_nearest_enclosing_handler()` in `codegen.py` and call it just before
`use_next_block(with_handler)` in `handle_withitem` (and the async-with equivalent).
Emit an `emit_exception_table_entry(with_handler, enclosing_handler, ...)` to cover the
with-handler block with the next enclosing scope's handler.

### Phase 11  -- Make `SETUP_WITH`/`SETUP_ASYNC_WITH` pseudo-instructions

**Goal:** Replace `SETUP_WITH` and `SETUP_ASYNC_WITH` with private negative constants
(same pattern as `_SETUP_FINALLY`/`_SETUP_CLEANUP`/`_POP_BLOCK` in Phase 9).  The
compiler emits `cm.__enter__()` as a plain `LOAD_ATTR` + `CALL` sequence; the pseudo
`_SETUP_WITH` marker is kept in `block.instructions` solely for the Phase 7 linear scan.
Remove the interpreter dispatch for these opcodes and bump the magic number.

### Phase 12  -- Split `last_instr` into display and execution pointers (requires benchmarking)

**Background:** CPython 3.11 maintains two separate pointers:
- `next_instr` (C local): execution pointer, used by `exception_unwind` for table lookup -- never saved in the frame
- `frame->prev_instr`: display pointer for `f_lasti`/`f_lineno`, overwritten by `RERAISE` to restore the original raise site

**Current PyPy state:** `last_instr` conflates both roles. The workaround is `_reraise_saved_lasti` (a second frame field).

**Goal:** Make `last_instr` display-only; use the local `next_instr` variable in `dispatch_bytecode` for table lookup. Removes `_reraise_saved_lasti` from every frame and reduces virtualizable writes on the hot path.

**Risk:** Must benchmark before landing. Do not land without benchmark data.

### Phase 13  -- Flow-graph-based exception table (adopt CPython model)

**Background:** CPython 3.11's compiler assigns each basic block an `except_stack` depth
at graph-construction time.  Duplicated blocks inherit this depth from the original, so the
exception table is always complete regardless of where copies are placed in the final layout.
PyPy's Phase 7 linear scan cannot achieve this because it operates on the final flat
instruction stream, after `duplicate_exits_without_lineno` has already appended copies past
all the SETUP/POP_BLOCK pairs that defined their original scope.

**Goal:** Replace Phase 7's linear scan with a flow-graph traversal that propagates handler
coverage through jump edges:
1. After `_finalize_blocks` (which runs `duplicate_exits_without_lineno`) but before
   `_build_code`, traverse the block graph from `first_block` following both fall-through
   (`next_block`) and explicit jump edges.  Maintain a handler stack at each block, seeded
   from the block's predecessor(s).
2. Each block records the handler that was active when it was first visited.  For a block
   with multiple predecessors, all predecessors must agree on the handler (they will, because
   `duplicate_exits_without_lineno` only copies blocks whose predecessors are all within the
   same handler scope).
3. Build the exception table from the per-block handler assignments rather than from the
   flat instruction stream.

**Effect on `duplicate_exits_without_lineno`:** `newtarget` is jumped to from `end_inner`,
which is inside the outer `try/except` scope.  The flow-graph traversal follows that edge
and assigns the outer handler to `newtarget`.  RERAISE in `newtarget` then dispatches
correctly to the outer except block -- the same behaviour as if `newtarget` had never been
copied out of range.  The per-case patches in `duplicate_exits_without_lineno` (e.g. the
RERAISE-only block guard) can be removed once Phase 13 is in place.

