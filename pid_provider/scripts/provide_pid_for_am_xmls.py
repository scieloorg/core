from pid_provider import tasks


def run(username, collection_acron=None, pids=None):
    if not collection_acron and not pids:
        return tasks.harvest_pids.apply_async(
            kwargs={
                "username": username,
                "stop": 100,
            }
        )

    if not pids:
        return tasks.harvest_pids.apply_async(
            kwargs={
                "username": username,
                "collection_acron": collection_acron,
                "stop": 100,
            }
        )

    if "," in pids:
        items = [
            {"collection_acron": collection_acron, "pid_v2": pid_v2}
            for pid_v2 in pids.split(",")
        ]
        return tasks.provide_pid_for_am_xmls.apply_async(
            kwargs={
                "username": username,
                "items": items,
            }
        )

    return tasks.provide_pid_for_am_xml.apply_async(
        kwargs={
            "username": username,
            "collection_acron": collection_acron,
            "pid_v2": pids,
        }
    )
