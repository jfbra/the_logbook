"""Code-defined, ordered grade lists, easiest first.

The order is the ranking the later statistics slice needs. The top of each list is the
hardest grade climbed to date, so extending a list is a one-line change. Keys are the
`GradeSystem` values. Sources disagree slightly at the easy end of Font and French, so
the lowest grade listed is the lowest commonly used.
"""

V_GRADES = ["VB", *(f"V{n}" for n in range(0, 18))]

_FONT_STEPS = ["A", "A+", "B", "B+", "C", "C+"]
FONT_GRADES = [
    "3",
    "4",
    "4+",
    "5",
    "5+",
    *(f"{n}{step}" for n in (6, 7, 8) for step in _FONT_STEPS),
    "9A",
]

_FRENCH_STEPS = ["a", "a+", "b", "b+", "c", "c+"]
FRENCH_GRADES = [
    "1",
    "2",
    "3",
    "3+",
    "4a",
    "4b",
    "4c",
    "5a",
    "5b",
    "5c",
    *(f"{n}{step}" for n in (6, 7, 8) for step in _FRENCH_STEPS),
    "9a",
    "9a+",
    "9b",
    "9b+",
    "9c",
]

EWBANK_GRADES = [str(n) for n in range(1, 40)]

GRADES_BY_SYSTEM: dict[str, list[str]] = {
    "v": V_GRADES,
    "font": FONT_GRADES,
    "french": FRENCH_GRADES,
    "ewbank": EWBANK_GRADES,
}
