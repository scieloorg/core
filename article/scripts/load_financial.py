from article import tasks, controller


def run(user, file_path):
    #tasks.load_funding_data.apply_async(args=(user, file_path))
    controller.read_file(user, file_path)

