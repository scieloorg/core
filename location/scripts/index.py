from django.core.management import call_command


def run():
    update_options = {"interactive": False}
    call_command("rebuild_index", **update_options)
