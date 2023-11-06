from bigbang.tasks import task_start


def run(username):
    task_start.apply_async(
        kwargs=dict(
            username=username,
        ))
