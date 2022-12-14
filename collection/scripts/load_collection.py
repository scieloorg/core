from collection import tasks


def run():
    tasks.task_load_collection.apply_async()
