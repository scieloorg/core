from pid_provider import tasks


def run(username, folder):
    tasks.load_xml_lists.apply_async(
        kwargs={"username": username, "jsonl_files_path": folder}
    )
