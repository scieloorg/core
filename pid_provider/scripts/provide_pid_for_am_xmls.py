import json

from pid_provider import tasks


def run(
    username, collections, limit=None, stop=None, force_update=None
):
    return tasks.provide_pid_for_am_xmls.apply_async(
        kwargs={
            "username": username,
            "collections": json.loads(collections),
            "force_update": force_update or False,
            "limit": int(limit or 1000),
            "stop": int(stop or 1000),
        }
    )
