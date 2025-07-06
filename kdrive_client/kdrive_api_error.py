"""kdrive api error wrapper"""

import json


class KDriveApiError(Exception):
    """Exception raised when an API error occurs."""

    def __init__(self, message, response, **kwargs):
        self.message = message
        self.response = response
        print(response)
        print(json.dumps(kwargs))
