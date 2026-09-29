"""Minimal Arabic shaping for pygame text.

SDL_ttf lays text out left to right, so Arabic comes out with its letters in
reverse order. Instead we do the two steps a text engine would do:

1. *Shaping*: replace each letter with its contextual presentation form
   (isolated / final / initial / medial, Unicode block U+FE70-U+FEFF), and
   lam + alef with the mandatory ligature.
2. *Ordering*: reverse the result, because it will be drawn left to right.

Only plain letters are handled (no vowel marks, no mixed Latin/Arabic lines),
which is all the game's titles need. The font must contain the presentation
forms; Amiri does.
"""

# Letter -> (first presentation form, number of forms). Four forms means the
# letter joins on both sides; two means it only joins to the letter before it.
_FORMS: dict[str, tuple[int, int]] = {
    "ء": (0xFE80, 1), "آ": (0xFE81, 2), "أ": (0xFE83, 2),
    "ؤ": (0xFE85, 2), "إ": (0xFE87, 2), "ئ": (0xFE89, 4),
    "ا": (0xFE8D, 2), "ب": (0xFE8F, 4), "ة": (0xFE93, 2),
    "ت": (0xFE95, 4), "ث": (0xFE99, 4), "ج": (0xFE9D, 4),
    "ح": (0xFEA1, 4), "خ": (0xFEA5, 4), "د": (0xFEA9, 2),
    "ذ": (0xFEAB, 2), "ر": (0xFEAD, 2), "ز": (0xFEAF, 2),
    "س": (0xFEB1, 4), "ش": (0xFEB5, 4), "ص": (0xFEB9, 4),
    "ض": (0xFEBD, 4), "ط": (0xFEC1, 4), "ظ": (0xFEC5, 4),
    "ع": (0xFEC9, 4), "غ": (0xFECD, 4), "ف": (0xFED1, 4),
    "ق": (0xFED5, 4), "ك": (0xFED9, 4), "ل": (0xFEDD, 4),
    "م": (0xFEE1, 4), "ن": (0xFEE5, 4), "ه": (0xFEE9, 4),
    "و": (0xFEED, 2), "ى": (0xFEEF, 2), "ي": (0xFEF1, 4),
}
_LAM = "ل"
# Alef variant -> isolated lam-alef ligature (the final form is +1).
_LAM_ALEF: dict[str, int] = {
    "آ": 0xFEF5, "أ": 0xFEF7, "إ": 0xFEF9, "ا": 0xFEFB,
}

ISOLATED, FINAL, INITIAL, MEDIAL = range(4)


def _joins_forward(unit: str) -> bool:
    """Can this unit connect to the letter after it?"""
    forms = _FORMS.get(unit)
    return forms is not None and forms[1] == 4


def shape(text: str) -> str:
    """Return ``text`` in presentation forms and visual (left-to-right) order."""
    units: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if char == _LAM and following in _LAM_ALEF:
            units.append(char + following)
            index += 2
        else:
            units.append(char)
            index += 1

    shaped: list[str] = []
    for position, unit in enumerate(units):
        joins_previous = position > 0 and _joins_forward(units[position - 1])
        if len(unit) == 2:  # lam-alef ligature only joins backwards
            shaped.append(chr(_LAM_ALEF[unit[1]] + (FINAL if joins_previous else ISOLATED)))
            continue
        forms = _FORMS.get(unit)
        if forms is None:
            shaped.append(unit)
            continue
        first, count = forms
        following = units[position + 1] if position + 1 < len(units) else ""
        joins_next = count == 4 and (following in _FORMS or len(following) == 2)
        if count == 1:
            form = ISOLATED
        elif joins_previous and joins_next:
            form = MEDIAL
        elif joins_previous:
            form = FINAL
        elif joins_next:
            form = INITIAL
        else:
            form = ISOLATED
        shaped.append(chr(first + form))
    return "".join(reversed(shaped))
