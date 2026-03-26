class UnsupportedInputProvider:
    """Placeholder input provider for the first read-only UI release."""

    def submit(self, *_args, **_kwargs):
        raise NotImplementedError("Interactive player input is not implemented in the first UI release.")
