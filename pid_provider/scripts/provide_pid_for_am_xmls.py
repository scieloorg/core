from pid_provider import tasks


def run(username, collection_acron, pids):

    if "," in pids:
        tasks.provide_pid_for_am_xmls.apply_async(
            kwargs={
                "username": username,
                "collection_acron": collection_acron,
                "pids": pids.split(","),
            }
        )
        return
    tasks.provide_pid_for_am_xml.apply_async(
        kwargs={
            "username": username,
            "collection_acron": collection_acron,
            "pid_v2": pids,
        }
    )
