class TocSectionGetError(Exception):
    def __init__(self, message):
        super().__init__(f"Error while getting TocSection: Requires value and language parameters")