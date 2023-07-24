from pid_provider import tasks


def run(username, begin_date, end_date, limit, pages):
    # executa a task imediatamente
    tasks.load_xml_lists_from_opac.apply_async(
        kwargs={
            "username": username,
            "begin_date": begin_date,
            "end_date": end_date,
            "limit": int(limit),
            "pages": int(pages),
        }
    )
