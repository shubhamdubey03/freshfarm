from django.apps import AppConfig


class CoreOrderConfig(AppConfig):
    name = 'core_order'

    def ready(self):
        import core_order.signals 
