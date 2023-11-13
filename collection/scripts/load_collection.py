from collection import tasks


def run(username):
    tasks.task_load_collections.apply_async(kwargs={"username": username})
