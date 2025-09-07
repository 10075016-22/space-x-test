from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
)
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from constructs import Construct
from cdk.interfaces.propsDynamoDb import PropsDynamoDb

class DynamoDBStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, propsDynamoDbStack: PropsDynamoDb, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal_policy = RemovalPolicy.DESTROY if propsDynamoDbStack["removal_policy"] == "Destroy" else RemovalPolicy.RETAIN

        # DynamoDB Table for backend data
        table = dynamodb.Table(
            self,
            "SpaceXLaunchesTable",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="sk",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            table_name=propsDynamoDbStack["table_name"],
        )

        # IAM Role for backend (Lambda) with write access to the table
        backend_role = iam.Role(
            self,
            "BackendLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for backend Lambda to access DynamoDB table",
        )

        # Basic Lambda execution permissions (e.g., CloudWatch Logs)
        backend_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Grant write permissions on the table to the backend role
        table.grant_write_data(backend_role)

        # Outputs for cross-stack/service references
        CfnOutput(self, "DynamoTableName", value=table.table_name)
        CfnOutput(self, "DynamoTableArn", value=table.table_arn)
        CfnOutput(self, "BackendRoleArn", value=backend_role.role_arn)
