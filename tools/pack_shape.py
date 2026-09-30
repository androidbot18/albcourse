"""Decide how a family is allowed to share a session with other families.

Option 2 of the sequencing review: a multi-member family -- one where a root
actually has derivations, so the root-based design has something to teach --
gets a level to itself. Single-member families carry no group lesson, so they
pack together up to the session target exactly as before.

Why not simply "one family per level"? Measured, that produces 3,033 levels
that are 83% single words. A level is a session, not an item. Why not allow a
multi-member family to pack with others? Because that is the original defect:
level 444 opened with six unrelated roots, so a root and its derivations never
unlocked together in a lesson the learner could see.

A family that alone exceeds the session target is split by the caller into
numbered continuation parts; each part is still a whole family on its own.
"""

SESSION_TARGET = 9
# How many single-member families may share one level. Singletons have no
# group lesson to protect, so this is only a shape control: it keeps a level
# from looking like a random word dump by capping how many roots it names.
MAX_SINGLETONS = 6
# A multi-member family may be joined by singletons, but only to fill the
# session up. Once it appears, nothing else starts a new group with it.
FILL_ONLY = True


def is_multi_member(n_members):
    """True when the family actually teaches a root plus its derivations."""
    return n_members > 1


def may_join(existing_families, incoming_members):
    """Can a family of `incoming_members` join a level already holding
    `existing_families` (a list of member-counts) without breaking the
    root-based design?

    Returns True when the level stays a coherent lesson:
      - a multi-member family never shares with a second family;
      - a singleton may join anything, subject to the caller's count cap.
    """
    if not existing_families:
        return True
    if len(existing_families) >= MAX_SINGLETONS:
        return False
    if is_multi_member(incoming_members):
        # At most one multi-member family leads a level. Two would be the
        # defect this whole change exists to remove: six unrelated roots in
        # one session, so no root ever unlocked together with its
        # derivations. A singleton cannot dilute that, because a singleton
        # has no group lesson to lose.
        return not any(is_multi_member(n) for n in existing_families)
    return True
