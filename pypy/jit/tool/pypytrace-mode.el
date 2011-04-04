(provide 'pypytrace-mode)
(eval-when-compile
  (require 'generic-x)
  (require 'hi-lock)
  (require 'compile)
  (require 'cus-edit))

(defun set-truncate-lines ()
  (setq truncate-lines t))

(define-generic-mode 
  'pypytrace-mode                   ;; name of the mode to create
  nil
  '("jump" "finish" "int_add" "int_sub" "int_mul" "int_floordiv" "uint_floordiv" "int_mod" "int_and" "int_or" "int_xor" "int_rshift" "int_lshift" "uint_rshift" "float_add" "float_sub" "float_mul" "float_truediv" "float_neg" "float_abs" "cast_float_to_int" "cast_int_to_float" "int_lt" "int_le" "int_eq" "int_ne" "int_gt" "int_ge" "uint_lt" "uint_le" "uint_gt" "uint_ge" "float_lt" "float_le" "float_eq" "float_ne" "float_gt" "float_ge" "int_is_zero" "int_is_true" "int_neg" "int_invert" "same_as" "ptr_eq" "ptr_ne" "arraylen_gc" "strlen" "strgetitem" "getfield_gc_pure" "getfield_raw_pure" "getarrayitem_gc_pure" "unicodelen" "unicodegetitem" "getarrayitem_gc" "getarrayitem_raw" "getfield_gc" "getfield_raw" "new" "new_with_vtable" "new_array" "force_token" "virtual_ref" "setarrayitem_gc" "setarrayitem_raw" "setfield_gc" "setfield_raw" "arraycopy" "newstr" "strsetitem" "unicodesetitem" "newunicode" "cond_call_gc_wb" "virtual_ref_finish" "call" "call_assembler" "call_may_force" "call_loopinvariant" "call_pure" "int_add_ovf" "int_sub_ovf" "int_mul_ovf") ;; keywords
  '( ;; additional regexps
    ("^# Loop.*" . 'hi-blue)
    ("\\[.*\\]" . 'font-lock-comment-face) ;; comment out argument lists
    ("guard_[a-z_]*" . 'widget-button-pressed)
    ("\\(ptr\\|p\\)[0-9][0-9]*" . 'font-lock-variable-name-face)
    ("i[0-9][0-9]*" . 'custom-button-pressed-unraised)
    ("\\(descr=<.*FieldDescr \\)\\([^ ]*\\.\\)\\([^ ]*\\)\\( .*>\\)"
     (1 'font-lock-comment-face)
     (2 'font-lock-variable-name-face)
     (3 'escape-glyph)
     (4 'font-lock-comment-face))
    ("<.*FieldDescr \\([^ ]*\\)" (1 'font-lock-variable-name-face))
    ;; comment out debug_merge_point, but then highlight specific part of it
    ("^debug_merge_point.*" . font-lock-comment-face)
    ("^\\(debug_merge_point\\).*code object\\(.*\\), file \\('.*'\\), \\(line .*\\)> \\(.*\\)"
     (1 'compilation-warning t)
     (2 'escape-glyph t)
     (3 'font-lock-string-face t)
     (4 'escape-glyph t)
     (5 'custom-variable-tag t)))
  '("\\.trace$")
  '(set-truncate-lines)
  "A mode for pypy traces files")

;; debug helpers
;; (switch-to-buffer-other-window "strslice2.trace")
;; (pypytrace-mode)

