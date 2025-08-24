import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item's Decimal types to JSON."""

    def default(self, o):
        if isinstance(o, Decimal):
            # Check if it's a float or int
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
