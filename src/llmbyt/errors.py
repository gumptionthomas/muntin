"""Every llmbyt failure derives from LlmbytError.

Errors are loud and instructive: name the constraint, the measured
violation, and the fix. They are the primary teaching surface for an
agent running in a harness with nothing else loaded.
"""


class LlmbytError(Exception):
    """Base for every llmbyt failure."""
