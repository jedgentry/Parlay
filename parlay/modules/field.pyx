
class _FieldClass(object):
    """
    All Fields must inherit from this class.
    This is the only sure-fire way that we can tell what class attributes are meant to be fields, and which are not

    Special User-defined fields should *not* inherit from this directly.
    Instead inherit from Topic or Content
    """

    def __init__(self, required=True):
        self.required = required

class Topic(_FieldClass):
    """
    Topics are fields that can be used to publish and subscribe to
    """
    pass


class Content(_FieldClass):
    """
    Content fields can *not* be used to subscribe to
    """
    pass




