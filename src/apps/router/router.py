from rest_framework.routers import DefaultRouter


class CommonRouter(DefaultRouter):
    def __init__(self, *args, **kwargs):
        """
        Add additional route to method mappings.
        """
        super().__init__(*args, **kwargs)

        # List route is in self.routes[0]
        self.routes[0].mapping["delete"] = "destroy_list"
