"""Every muntin failure derives from MuntinError.

Errors are loud and instructive: name the constraint, the measured
violation, and the fix. They are the primary teaching surface for an
agent running in a harness with nothing else loaded.
"""


class MuntinError(Exception):
    """Base for every muntin failure."""
