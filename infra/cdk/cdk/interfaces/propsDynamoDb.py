from typing import TypedDict

class PropsDynamoDb(TypedDict):
    table_name: str
    removal_policy: str