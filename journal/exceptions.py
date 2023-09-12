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
