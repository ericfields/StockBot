"""Abstract class representing an interface for retrieving stock quote information
given various identifiers"""
class QuoteHandler():

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

    def get_instrument(instrument_uuid):
        """Should return an instrument given its UUID id value
        Should raise a BadRequestException if the instrument was not found
        """
        raise Exception("Not implemented")


    def search_for_instrument(instrument):
        """Should return an instrument given a string representing its unique identifier,
        such as would be returned by `instrument_identifier(instrument)`
        """
        raise Exception("Not implemented")

    def instrument_full_name(instrument):
        """Should return a full name for the instrument for use as its chart title
        """
        raise Exception("Not implemented")

    def instrument_simple_name(instrument):
        """Should return a short name for the instrument used when quoting multiple
        instruments at once
        """
        raise Exception("Not implemented")

    def instrument_identifier(instrument):
        """Should return a string representing a unique identifier which matches
        the `FORMAT` regular expression, and which can be used to search for
        the instrument uniquely.
        """
        raise Exception("Not implemented")
