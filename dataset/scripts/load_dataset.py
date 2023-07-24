from dataset import tasks


def run():
    tasks.load_dataset.apply_async()