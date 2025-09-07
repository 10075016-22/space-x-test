#!/usr/bin/env python3
import os
import aws_cdk as cdk
from cdk.DynamoDBStack import DynamoDBStack
from cdk.interfaces.propsDynamoDb import PropsDynamoDb
from dotenv import load_dotenv

load_dotenv()

app = cdk.App()

propsDynamoDbStack: PropsDynamoDb = {
    "table_name": os.getenv("TABLE_NAME"),
    "removal_policy": os.getenv("REMOVAL_POLICY"),
}

DynamoDBStack(app, "SpaceX-DynamoDBStack", propsDynamoDbStack=propsDynamoDbStack)

app.synth()
