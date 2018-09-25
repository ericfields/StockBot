"""Abstract class representing an interface for retrieving stock quote information
given various identifiers"""
class Handler():

    TYPE = None
    """str: Simple string indicating what type of security this quote handler
    processes, e.g.. 'stock', 'option'..."""

    FORMAT = None
    """str: Regular expression representing the format of a unique identifier
    that can represent a single security"""

    EXAMPLE = None
    """str: Example string of a unique identifier format that a user can provide
    when searching for a quote. Should match the `FORMAT` provided
    """

    AUTHENTICATED = None
    """bool: Whether or not an authenticated Robinhood account is required to
    quote this type of entity"""

    def get_instrument(instrument_uuid):
        """Should return an instrument given its UUID id value
        Should raise a BadRequestException if the instrument was not found
        """
        raise Exception("Not implemented")


    def search_for_instrument(instrument):
        """Should return an instrument given a string representing its unique identifier,
        such as would be returned by `Instrument.identifier`
        """
        raise Exception("Not implemented")
