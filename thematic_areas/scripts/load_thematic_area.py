from thematic_areas import tasks


def run():
    tasks.load_thematic_area.apply_async()
