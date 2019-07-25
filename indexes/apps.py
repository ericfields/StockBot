from django.apps import AppConfig
from django.db import connection
import sys

class IndexesConfig(AppConfig):
    name = 'indexes'

    def ready(self):
        if {'runserver', 'uwsgi'}.intersection(set(sys.argv)):
            from indexes.models import Index
            DATABASE_PRESENT = bool(connection.settings_dict['NAME'])
            
            if DATABASE_PRESENT and Index._meta.db_table in connection.introspection.table_names():
                # Preload instruments in users' indexes
                from quotes.aggregator import Aggregator
                import logging
                logger = logging.getLogger('stockbot')
                logger.info("Preloading index instruments")
                aggregator = Aggregator(*Index.objects.all())
