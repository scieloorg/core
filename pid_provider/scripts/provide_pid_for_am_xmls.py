from pid_provider import tasks


def run(username, collection_acron, pid_v2):
    tasks.provide_pid_for_am_xml.apply_async(
        kwargs={
            "username": username,
            "collection_acron": collection_acron,
            "pid_v2": pid_v2,
        }
    )
