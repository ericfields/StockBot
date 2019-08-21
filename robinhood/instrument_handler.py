from helpers.cache import Cache
from helpers.pool import thread_pool
from robinhood.api import ApiResource
from exceptions import *
import re

CACHE_DURATION = 86400

"""Abstract class representing an interface for retrieving asset quote information
given various identifiers"""
class InstrumentHandler():

    TYPE = None
    """str: Simple string indicating what type of asset this quote handler
    processes, e.g.. 'stock', 'option'..."""

    FORMAT = None
    """str: Regular expression representing the format of a unique identifier
    that can represent a single asset"""

    EXAMPLE = None
    """str: Example string of a unique identifier format that a user can provide
    when searching for a quote. Should match the `FORMAT` provided
    """

    def instrument_class(self):
        """class: Robinhood instrument class this handler is used for."""
        raise Exception("Not implemented")

    def get_search_params(self, identifier):
        """dict: Given an identifier, returns a dictionary of parameters which should be used to
        make a search request to Robinhood for a single resource matching this identifier's
        parameters."""
        raise Exception("Not implemented")

    def authenticated(self):
        """bool: Whether or not instrument retrieval is authenticated. Defaults to False."""
        return False

    def filter_results(self, instruments, params):
        """instrument: An optional filter to determine a single instrument to select from
        a search query that returns multiple results. If a unique result matching the
        parameters is found, it should return a list containing a single result. Otherwise
        it should return a list containing all matching results, or an empty list
        if no matching result was found."""
        return instruments

    def standard_identifier(self, identifier):
        """str: Given an identifier, return a standardized string representation.
        Since identifier formats can be quite varied, this method allows us to
        detemrine an identifier format which can be used as a unique identifier
        for a stock universally."""
        raise BadRequestException("Not implemented")

    ### End of methods/fields to implement

    UUID_FORMAT = '.*\/?([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\/?$'

    def find_instruments(self, *identifiers):
        if self.authenticated():
            self.check_authentication()

        # Map of identifiers to their corresponding instruments
        instrument_map = {}

        get_params = {}
        search_params = {}

        for identifier in identifiers:
            if type(identifier) != str:
                raise Exception("Expected a string identifier, but was a {}".format(type(identifier)))
            if self.valid_url(identifier):
                id = re.match(self.UUID_FORMAT, identifier)[1]
                get_params[identifier] = id
            elif re.match(self.FORMAT, identifier):
                params = self.get_search_params(identifier)
                search_params[identifier] = params
            else:
                raise BadRequestException("Invalid {} identifier: '{}'".format(self.TYPE, identifier))

        # Fetch instruments in get_params all at once in a batch query
        self.get_instruments(instrument_map, get_params)
        # Fetch remaining unknown instruments in a search query
        self.search_instruments(instrument_map, search_params)

        return instrument_map

    def get_instruments(self, instrument_map, get_params):
        ids_to_retrieve = set()

        for url in get_params:
            # Check if instrument is in the cache before querying Robinhood
            data = Cache.get(url)
            if data:
                instrument = self.instrument_class()(**data)
                self.set_instrument(instrument_map, instrument)
            else:
                id = get_params[url]
                ids_to_retrieve.add(id)

        # Perform a batch query for the rest of the ids
        if ids_to_retrieve:
            retrieved_instruments = self.instrument_class().search(ids=ids_to_retrieve)
            for instrument in retrieved_instruments:
                self.set_instrument(instrument_map, instrument)

                # Cache results of both a resource get and a search query
                Cache.set(instrument.url, instrument.data, CACHE_DURATION)
                search_url = self.build_search_url(self.get_search_params(instrument.identifier()))
                Cache.set(search_url, {'results': [instrument.data]}, CACHE_DURATION)

    def search_instruments(self, instrument_map, search_params):
        search_jobs = {}

        # Initiate a thread pool for these requests.
        # Using a shared thread pool can cause hanging
        # when using a multi-process runner such as uwsgi.
        with thread_pool(10) as pool:
            for identifier in search_params:
                instrument = None
                params = search_params[identifier]
                search_url = self.build_search_url(params)

                data = Cache.get(search_url)
                if data:
                    if 'results' in data:
                        cached_instruments = [self.instrument_class()(**d) for d in data['results']]
                        if len(cached_instruments) > 1:
                            cached_instruments = self.filter_results(cached_instruments, params)
                        if len(cached_instruments) == 1:
                            instrument = cached_instruments[0]
                    else:
                        instrument = self.instrument_class()(**data)

                if instrument:
                    self.set_instrument(instrument_map, instrument, identifier)
                else:
                    search_jobs[identifier] = pool.call(self.instrument_class().search, **params)

        for identifier in search_jobs:
            params = search_params[identifier]
            search_job = search_jobs[identifier]
            retrieved_instruments = search_job.get()
            search_url = self.build_search_url(params)

            # Cache results for the search query
            Cache.set(search_url, {'results': [ i.data for i in retrieved_instruments ]}, CACHE_DURATION)

            matching_instruments = self.filter_results(retrieved_instruments, params)

            if len(matching_instruments) == 0:
                raise NotFoundException("No {}s found for {}".format(self.TYPE, identifier))
            elif len(matching_instruments) > 1:
                raise Exception("Multiple possible {}s found for {}, could not select a unique one".format(self.TYPE, identifier))

            instrument = matching_instruments[0]
            self.set_instrument(instrument_map, instrument, identifier)

            # Cache results for the resource query
            Cache.set(instrument.url, instrument.data, CACHE_DURATION)

    def set_instrument(self, instrument_map, instrument, identifier=None):
        instrument_map[instrument.identifier()] = instrument
        instrument_map[instrument.url] = instrument
        if identifier:
            instrument_map[identifier] = instrument
            instrument_map[self.standard_identifier(identifier)] = instrument

    def valid_identifier(self, identifier):
        return self.valid_url(identifier) or re.match(self.FORMAT, identifier)

    def valid_url(self, url):
        return url.startswith(self.instrument_class().base_url()) and re.match(self.UUID_FORMAT, url)

    def check_authentication(self):
        if not (ApiResource.username and ApiResource.password):
            raise ConfigurationException("This command requires an authenticated backend API call, but credentials are not configured for this server.")

    def build_search_url(self, params):
        # params is a dictionary of parameters to search for
        return self.instrument_class().search_url(**params)
