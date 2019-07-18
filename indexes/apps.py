from django.apps import AppConfig
from django.db import connection
import sys

class IndexesConfig(AppConfig):
    name = 'indexes'

    def ready(self):
        # Preload instruments in users' indexes
        if not 'test' in sys.argv: # Don't do this if just running unit tests
            from indexes.models import Index
            from quotes.aggregator import Aggregator
            import logging
            logger = logging.getLogger('stockbot')

            DATABASE_PRESENT = bool(connection.settings_dict['NAME'])

            if DATABASE_PRESENT and Index._meta.db_table in connection.introspection.table_names():
                logger.info("Preloading index instruments")
                aggregator = Aggregator(*Index.objects.all())
