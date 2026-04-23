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
| 10 | Flow-graph-based exception table to fix `duplicate_exits_without_lineno` gap | High | In progress |
| 10a | Make `dis.dis` show exception table entries (`show_exception_entries` kwarg) | Medium | Not started |
| 11 | Verify/clean up remaining exception table coverage gaps after Phase 10 | Low | Not started |
| 12 | Make `SETUP_WITH`/`SETUP_ASYNC_WITH` pseudo-instructions; emit `__enter__` as plain call from compiler | Medium | Not started |
| 13 | Split `last_instr` into display/execution pointers (requires benchmarking) | Medium | Not started |

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

### Phase 10  -- Flow-graph-based exception table (adopt CPython model)

**Background:** CPython 3.11's compiler assigns each basic block an `except_stack` at
graph-construction time.  Duplicated blocks inherit this depth from the original, so the
exception table is always complete regardless of where copies are placed in the final layout.
PyPy's Phase 7 linear scan cannot achieve this because it operates on the final flat
instruction stream, after `duplicate_exits_without_lineno` has already appended copies past
all the SETUP/POP_BLOCK pairs that defined their original scope.

**Symptoms:** `test_shutil.TestCopyFile.test_w_dest_close_fails` / `test_w_source_close_fails`.
The inner `with open(dst)` body contains multiple fast-path `return` statements that trigger
`duplicate_exits_without_lineno`.  The duplicate exit blocks each contain a `_POP_BLOCK` for
the inner with scope at the same byte offset as the preceding GiveupOnFastCopy `_POP_BLOCK`.
The linear scan sees a zero-range close for the inner with handler and defers it with
`rs=-1` (discard).  The fallback `copyfileobj` call that follows has no exception table
coverage from the inner with handler, so `AttributeError` from `copyfileobj` bypasses
`fdst.__exit__` entirely.  Reproducer: `pypy/interpreter/test/apptest_with_leak.py::test_shutil_pattern`.

**Goal:** Replace the Phase 7 linear scan with a flow-graph traversal that propagates handler
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
RERAISE-only block guard) can be removed once Phase 10 is in place.

### Phase 11  -- Verify/clean up remaining coverage gaps after Phase 10

After Phase 10's graph traversal is in place, run the full test suite and check whether
any exception table coverage gaps remain (e.g. with-handler blocks not covered by the
enclosing scope's handler).  The original Phase 10 codegen fix (`_nearest_enclosing_handler`
in `codegen.py`) may or may not still be needed depending on what the graph traversal
handles automatically.

### Phase 12  -- Make `SETUP_WITH`/`SETUP_ASYNC_WITH` pseudo-instructions

**Goal:** Replace `SETUP_WITH` and `SETUP_ASYNC_WITH` with private negative constants
(same pattern as `_SETUP_FINALLY`/`_SETUP_CLEANUP`/`_POP_BLOCK` in Phase 9).  The
compiler emits `cm.__enter__()` as a plain `LOAD_ATTR` + `CALL` sequence; the pseudo
`_SETUP_WITH` marker is kept in `block.instructions` solely for the Phase 10 graph scan.
Remove the interpreter dispatch for these opcodes and bump the magic number.

### Phase 13  -- Split `last_instr` into display and execution pointers (requires benchmarking)

**Background:** CPython 3.11 maintains two separate pointers:
- `next_instr` (C local): execution pointer, used by `exception_unwind` for table lookup -- never saved in the frame
- `frame->prev_instr`: display pointer for `f_lasti`/`f_lineno`, overwritten by `RERAISE` to restore the original raise site

**Current PyPy state:** `last_instr` conflates both roles. The workaround is `_reraise_saved_lasti` (a second frame field).

**Goal:** Make `last_instr` display-only; use the local `next_instr` variable in `dispatch_bytecode` for table lookup. Removes `_reraise_saved_lasti` from every frame and reduces virtualizable writes on the hot path.

**Risk:** Must benchmark before landing. Do not land without benchmark data.

---

## Phase 10 -- Current implementation status (stashed, in progress)

**Approach chosen:** Mark `newtarget` blocks created by `duplicate_exits_without_lineno`
with `_is_dup_exit = True`.  In `_build_exceptiontable`, when the linear scan processes
a jump instruction whose target is a `_is_dup_exit` block, save the current scope state
`(cur_handler, handler_stack, cur_lasti, cur_depth_adjust, cur_depth_sub)` in
`dup_block_states[target]`.  On arrival at the `_is_dup_exit` block, restore that state
before continuing the linear scan.  This is cheaper and more targeted than the prior
BFS approach, which incorrectly assigned handler scope to conditional-jump targets
(e.g. `exit2` in `handle_withitem`) that exit the scope without a `_POP_BLOCK`.

**What passes:** `test_with_reraise_2`, `test_revert_exc_info_2_finally` -- both fixed.
Full `pypy/interpreter` suite: 2914 passed, 53 skipped, 3 failed.

**What still fails:**
- `test_shutil_pattern` -- the original target bug, still broken.
- `test_try_except_star_exception_not_caught` / `test_try_except_star_named_exception_not_caught`
  -- likely pre-existing (except* / PEP 654), need to verify.

**Root cause of remaining `test_shutil_pattern` failure:** Unknown -- the fix should
apply (newtarget blocks from early returns inside the inner with body), but the state
save/restore is apparently not firing or not correct.  Next step: use `dis.dis(copyfile)`
inside the apptest to inspect the generated exception table, which requires Phase 10a
(implement `show_exception_entries` in PyPy's `dis` module) first.

**Files changed (stashed):**
- `pypy/interpreter/astcompiler/assemble.py`: `Block._is_dup_exit`, mark in
  `duplicate_exits_without_lineno`, new `_build_exceptiontable` with `dup_block_states`.
- `exceptiontable.md`: this status update.

