from django.apps import AppConfig
from django.db import connection

class PortfoliosConfig(AppConfig):
    name = 'portfolios'

    def ready(self):
        # Preload instruments in users' portfolios
        from portfolios.models import Portfolio
        from quotes.aggregator import Aggregator
        import logging
        logger = logging.getLogger('stockbot')

        DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

        if DATABASE_PRESENT and Portfolio._meta.db_table in connection.introspection.table_names():
            logger.info("Preloading portfolio instruments")
            aggregator = Aggregator(*Portfolio.objects.all())
