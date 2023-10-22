class MissionCreateOrUpdateError(Exception):
    ...


class MissionGetError(Exception):
    ...


class JournalCreateOrUpdateError(Exception):
    ...


class JournalGetError(Exception):
    ...


class OfficialJournalCreateOrUpdateError(Exception):
    ...


class OfficialJournalGetError(Exception):
    ...


class SciELOJournalCreateOrUpdateError(Exception):
    ...


class SciELOJournalGetError(Exception):
    ...


class StandardCreationOrUpdateError(Exception):
    def __init__(self, code, message):
        super().__init__(f"Unable to create or update Standard with code: {code}: {str(message)}")


class SubjectCreationOrUpdateError(Exception):
    def __init__(self, code, message):
        super().__init__(f"Unable to create or update Subject with code: {code}: {str(message)}")


class WosdbCreationOrUpdateError(Exception):
    def __init__(self, code, message):
        super().__init__(f"Unable to create or update WebOfKnowledge with code: {code}: {str(message)}")


class IndexedAtCreationOrUpdateError(Exception):
    def __init__(self, name, acronym, message):
        super().__init__(f"Unable to create or update IndexedAt with name: {name} and acronym: {acronym}: {str(message)}")


class AddIssnScieloToTabsError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add ISSN SciELO Tabs from {str(obj)}: {str(message)}")


class AddIssnsToTabsError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add ISSN's Tabs from {str(obj)}: {str(message)}")


class AddTitleAtScieloError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Title at SciELO Tabs from {str(obj)}: {str(message)}")


class AddTitleThematicAreasError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Title Thematic Areas Tabs from {str(obj)}: {str(message)}")


class AddTitleCurrentStatusError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Title Current Status Tabs from {str(obj)}: {str(message)}")


class AddTitleSubtitleScieloError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Title and Subtitle SciELO Tabs from {str(obj)}: {str(message)}")


class AddShortTitleScieloError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Short Title SciELO Tabs from {str(obj)}: {str(message)}")


class AddPublisherNameError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Publisher Name Tabs from {str(obj)}: {str(message)}")


class AddUseLicenseError(Exception):
    def __init__(self, message, obj):
        super().__init__(f"Unable to add Use License Tabs from {str(obj)}: {str(message)}")
