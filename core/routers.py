from haystack import routers


class UpdateEverythingRouter(routers.BaseRouter):
    def for_write(self, **hints):
        return ("default", "oai")
