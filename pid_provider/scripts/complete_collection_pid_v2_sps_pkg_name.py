from pid_provider.tasks import task_complete_collection_pid_v2_sps_pkg_name


def run(username, force_update=None):
    task_complete_collection_pid_v2_sps_pkg_name.apply_async(
        kwargs={
            "username": username,
            "force_update": force_update in ("true", "True", "1"),
        }
    )
