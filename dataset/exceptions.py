class DataverseGetError(Exception):
    def __init__(self):
        super().__init__(f"Dataverse.get requires identifier or name:")

class DataverseCreateOrUpdateError(Exception):
    def __init__(self, message):
        super().__init__(f"Unable to create or update Dataverse: {message}")

class DatasetGetError(Exception):
    def __init__(self):
        super().__init__(f"Dataset.get requires global_id")

class DatasetCreateOrUpdateError(Exception):
    def __init__(self, message):
        super().__init__(f"Unable to create or update Dataset: {message}")

class FileGetError(Exception):
    def __init__(self):
        super().__init__(f"File.get requires file persistent id")

class FileCreateOrUpdateError(Exception):
    def __init__(self, message):
        super().__init__(f"Unable to create or update File: {message}")    
