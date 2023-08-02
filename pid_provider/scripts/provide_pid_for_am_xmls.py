from pid_provider import tasks


def run(
    username, collection_acron, from_date=None, limit=None, stop=None, force_update=None
):
    return tasks.harvest_pids.apply_async(
        kwargs={
            "username": username,
            "collection_acron": collection_acron,
            "from_date": from_date or "1900-01-01",
            "limit": int(limit or 1000),
            "force_update": force_update or False,
            "stop": int(stop or 1000),
        }
    )
