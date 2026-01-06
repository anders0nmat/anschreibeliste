
class NoLabelSuffixMixin:
    def __init__(self, *args, label_suffix=None, **kwargs):
        super().__init__(*args, label_suffix=label_suffix if label_suffix is not None else "", **kwargs)
    