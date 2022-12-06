import logging
from altmetric.tasks import load_altmetric


def run(*args):
    if args:
        logging.info(args)
        try:
            load_altmetric.apply_async(kwargs={"user_id": args[0], "file_path": args[1]})
        except Exception as e:
            logging.info(e)
            logging.info("The 'User ID' and the 'path' to Altmetric files is required.")
            logging.info("'User ID' must be an integer and 'path' must be a string")
    else:
        logging.info("The User ID and the path to Altmetric files is required.")