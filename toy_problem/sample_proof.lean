
theorem reverse_reverse (l : List Nat) : l.reverse.reverse = l := by
  induction l with
  | nil => simp
  | cons x xs ih =>
    rw [List.reverse_cons, List.reverse_append, ih]
    simp
