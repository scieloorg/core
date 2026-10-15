from collection import tasks


def run(username):
    tasks.task_complete_network_classification.apply_async(
        kwargs={"username": username}
    )
