"""Example runtime plug-in adding Ruby support."""


def register():
    """Return a mapping for Ruby language support."""
    return {"ruby": ["ruby"]}
