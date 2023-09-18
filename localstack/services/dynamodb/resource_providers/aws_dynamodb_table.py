# LocalStack Resource Provider Scaffolding v2
from __future__ import annotations

from pathlib import Path
from typing import Optional, Type, TypedDict

import localstack.services.cloudformation.provider_utils as util
from localstack.services.cloudformation.resource_provider import (
    CloudFormationResourceProviderPlugin,
    OperationStatus,
    ProgressEvent,
    ResourceProvider,
    ResourceRequest,
)


class DynamoDBTableProperties(TypedDict):
    KeySchema: Optional[list[KeySchema] | dict]
    Arn: Optional[str]
    AttributeDefinitions: Optional[list[AttributeDefinition]]
    BillingMode: Optional[str]
    ContributorInsightsSpecification: Optional[ContributorInsightsSpecification]
    DeletionProtectionEnabled: Optional[bool]
    GlobalSecondaryIndexes: Optional[list[GlobalSecondaryIndex]]
    ImportSourceSpecification: Optional[ImportSourceSpecification]
    KinesisStreamSpecification: Optional[KinesisStreamSpecification]
    LocalSecondaryIndexes: Optional[list[LocalSecondaryIndex]]
    PointInTimeRecoverySpecification: Optional[PointInTimeRecoverySpecification]
    ProvisionedThroughput: Optional[ProvisionedThroughput]
    SSESpecification: Optional[SSESpecification]
    StreamArn: Optional[str]
    StreamSpecification: Optional[StreamSpecification]
    TableClass: Optional[str]
    TableName: Optional[str]
    Tags: Optional[list[Tag]]
    TimeToLiveSpecification: Optional[TimeToLiveSpecification]


class AttributeDefinition(TypedDict):
    AttributeName: Optional[str]
    AttributeType: Optional[str]


class KeySchema(TypedDict):
    AttributeName: Optional[str]
    KeyType: Optional[str]


class Projection(TypedDict):
    NonKeyAttributes: Optional[list[str]]
    ProjectionType: Optional[str]


class ProvisionedThroughput(TypedDict):
    ReadCapacityUnits: Optional[int]
    WriteCapacityUnits: Optional[int]


class ContributorInsightsSpecification(TypedDict):
    Enabled: Optional[bool]


class GlobalSecondaryIndex(TypedDict):
    IndexName: Optional[str]
    KeySchema: Optional[list[KeySchema]]
    Projection: Optional[Projection]
    ContributorInsightsSpecification: Optional[ContributorInsightsSpecification]
    ProvisionedThroughput: Optional[ProvisionedThroughput]


class LocalSecondaryIndex(TypedDict):
    IndexName: Optional[str]
    KeySchema: Optional[list[KeySchema]]
    Projection: Optional[Projection]


class PointInTimeRecoverySpecification(TypedDict):
    PointInTimeRecoveryEnabled: Optional[bool]


class SSESpecification(TypedDict):
    SSEEnabled: Optional[bool]
    KMSMasterKeyId: Optional[str]
    SSEType: Optional[str]


class StreamSpecification(TypedDict):
    StreamViewType: Optional[str]


class Tag(TypedDict):
    Key: Optional[str]
    Value: Optional[str]


class TimeToLiveSpecification(TypedDict):
    AttributeName: Optional[str]
    Enabled: Optional[bool]


class KinesisStreamSpecification(TypedDict):
    StreamArn: Optional[str]


class S3BucketSource(TypedDict):
    S3Bucket: Optional[str]
    S3BucketOwner: Optional[str]
    S3KeyPrefix: Optional[str]


class Csv(TypedDict):
    Delimiter: Optional[str]
    HeaderList: Optional[list[str]]


class InputFormatOptions(TypedDict):
    Csv: Optional[Csv]


class ImportSourceSpecification(TypedDict):
    InputFormat: Optional[str]
    S3BucketSource: Optional[S3BucketSource]
    InputCompressionType: Optional[str]
    InputFormatOptions: Optional[InputFormatOptions]


REPEATED_INVOCATION = "repeated_invocation"


def get_ddb_provisioned_throughput(
    properties: dict,
) -> dict | None:
    # see https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html#cfn-dynamodb-table-provisionedthroughput
    args = properties.get("ProvisionedThroughput")
    if args == "AWS::NoValue":
        return None
    is_ondemand = properties.get("BillingMode") == "PAY_PER_REQUEST"
    # if the BillingMode is set to PAY_PER_REQUEST, you cannot specify ProvisionedThroughput
    # if the BillingMode is set to PROVISIONED (default), you have to specify ProvisionedThroughput

    if args is None:
        if is_ondemand:
            # do not return default value if it's on demand
            return

        # return default values if it's not on demand
        return {
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5,
        }

    if isinstance(args["ReadCapacityUnits"], str):
        args["ReadCapacityUnits"] = int(args["ReadCapacityUnits"])
    if isinstance(args["WriteCapacityUnits"], str):
        args["WriteCapacityUnits"] = int(args["WriteCapacityUnits"])

    return args


def get_ddb_global_sec_indexes(
    properties: dict,
) -> list | None:
    args: list = properties.get("GlobalSecondaryIndexes")
    is_ondemand = properties.get("BillingMode") == "PAY_PER_REQUEST"
    if not args:
        return

    for index in args:
        # we ignore ContributorInsightsSpecification as not supported yet in DynamoDB and CloudWatch
        index.pop("ContributorInsightsSpecification", None)
        provisioned_throughput = index.get("ProvisionedThroughput")
        if is_ondemand and provisioned_throughput is None:
            pass  # optional for API calls
        elif provisioned_throughput is not None:
            # convert types
            if isinstance((read_units := provisioned_throughput["ReadCapacityUnits"]), str):
                provisioned_throughput["ReadCapacityUnits"] = int(read_units)
            if isinstance((write_units := provisioned_throughput["WriteCapacityUnits"]), str):
                provisioned_throughput["WriteCapacityUnits"] = int(write_units)
        else:
            raise Exception("Can't specify ProvisionedThroughput with PAY_PER_REQUEST")
    return args


def get_ddb_kinesis_stream_specification(
    properties: dict,
) -> dict:
    args = properties.get("KinesisStreamSpecification")
    if args:
        args["TableName"] = properties["TableName"]
    return args


class DynamoDBTableProvider(ResourceProvider[DynamoDBTableProperties]):

    TYPE = "AWS::DynamoDB::Table"  # Autogenerated. Don't change
    SCHEMA = util.get_schema_path(Path(__file__))  # Autogenerated. Don't change

    def create(
        self,
        request: ResourceRequest[DynamoDBTableProperties],
    ) -> ProgressEvent[DynamoDBTableProperties]:
        """
        Create a new resource.

        Primary identifier fields:
          - /properties/TableName

        Required properties:
          - KeySchema

        Create-only properties:
          - /properties/TableName
          - /properties/ImportSourceSpecification

        Read-only properties:
          - /properties/Arn
          - /properties/StreamArn

        IAM permissions required:
          - dynamodb:CreateTable
          - dynamodb:DescribeImport
          - dynamodb:DescribeTable
          - dynamodb:DescribeTimeToLive
          - dynamodb:UpdateTimeToLive
          - dynamodb:UpdateContributorInsights
          - dynamodb:UpdateContinuousBackups
          - dynamodb:DescribeContinuousBackups
          - dynamodb:DescribeContributorInsights
          - dynamodb:EnableKinesisStreamingDestination
          - dynamodb:DisableKinesisStreamingDestination
          - dynamodb:DescribeKinesisStreamingDestination
          - dynamodb:ImportTable
          - dynamodb:ListTagsOfResource
          - dynamodb:TagResource
          - dynamodb:UpdateTable
          - kinesis:DescribeStream
          - kinesis:PutRecords
          - iam:CreateServiceLinkedRole
          - kms:CreateGrant
          - kms:Decrypt
          - kms:Describe*
          - kms:Encrypt
          - kms:Get*
          - kms:List*
          - kms:RevokeGrant
          - logs:CreateLogGroup
          - logs:CreateLogStream
          - logs:DescribeLogGroups
          - logs:DescribeLogStreams
          - logs:PutLogEvents
          - logs:PutRetentionPolicy
          - s3:GetObject
          - s3:GetObjectMetadata
          - s3:ListBucket

        """
        model = request.desired_state

        if not request.custom_context.get(REPEATED_INVOCATION):
            properties = [
                "TableName",
                "AttributeDefinitions",
                "KeySchema",
                "BillingMode",
                "ProvisionedThroughput",
                "LocalSecondaryIndexes",
                "GlobalSecondaryIndexes",
                "StreamSpecification",
                "Tags",
            ]

            if "TableName" not in model:
                model["TableName"] = util.generate_default_name(
                    request.stack_id, request.logical_resource_id
                )

            if model.get("ProvisionedThroughput"):
                model["ProvisionedThroughput"] = get_ddb_provisioned_throughput(model)

            if model.get("GlobalSecondaryIndexes"):
                model["GlobalSecondaryIndexes"] = get_ddb_global_sec_indexes(model)

            model["StreamSpecification"] = {
                **model.get("StreamSpecification", {}),
                **{"StreamEnabled": True},
            }

            create_params = util.select_attributes(model, properties)
            result = request.aws_client_factory.dynamodb.create_table(**create_params)

            model["Arn"] = result["TableDescription"]["TableArn"]
            if result["TableDescription"].get("LatestStreamArn"):
                model["StreamArn"] = result["TableDescription"]["LatestStreamArn"]

            request.custom_context[REPEATED_INVOCATION] = True
            return ProgressEvent(
                status=OperationStatus.IN_PROGRESS,
                resource_model=model,
                custom_context=request.custom_context,
            )

        description = request.aws_client_factory.dynamodb.describe_table(
            TableName=model["TableName"]
        )
        if description["Table"]["TableStatus"] != "ACTIVE":
            return ProgressEvent(
                status=OperationStatus.IN_PROGRESS,
                resource_model=model,
                custom_context=request.custom_context,
            )

        if model.get("KinesisStreamSpecification"):
            description = (
                request.aws_client_factory.dynamodb.describe_kinesis_streaming_destination(
                    model["TableName"]
                )
            )
            stream_destinations = description["KinesisDataStreamDestinations"]
            if not stream_destinations:
                request.aws_client_factory.dynamodb.enable_kinesis_streaming_destination(
                    **get_ddb_kinesis_stream_specification(model)
                )
                return ProgressEvent(
                    status=OperationStatus.IN_PROGRESS,
                    resource_model=model,
                    custom_context=request.custom_context,
                )
            elif stream_destinations[0]["DestinationStatus"] == "FAILED":
                return ProgressEvent(
                    status=OperationStatus.FAILED,
                    resource_model=model,
                    message="Kinesis stream destination failed",
                )
            elif stream_destinations[0]["DestinationStatus"] != "ACTIVE":
                return ProgressEvent(
                    status=OperationStatus.IN_PROGRESS,
                    resource_model=model,
                    custom_context=request.custom_context,
                )

        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_model=model,
        )

    def read(
        self,
        request: ResourceRequest[DynamoDBTableProperties],
    ) -> ProgressEvent[DynamoDBTableProperties]:
        """
        Fetch resource information

        IAM permissions required:
          - dynamodb:DescribeTable
          - dynamodb:DescribeContinuousBackups
          - dynamodb:DescribeContributorInsights
        """
        raise NotImplementedError

    def delete(
        self,
        request: ResourceRequest[DynamoDBTableProperties],
    ) -> ProgressEvent[DynamoDBTableProperties]:
        """
        Delete a resource

        IAM permissions required:
          - dynamodb:DeleteTable
          - dynamodb:DescribeTable
        """
        model = request.desired_state
        request.aws_client_factory.dynamodb.delete_table(TableName=model["TableName"])
        return ProgressEvent(
            status=OperationStatus.SUCCESS,
            resource_model={},
        )

    def update(
        self,
        request: ResourceRequest[DynamoDBTableProperties],
    ) -> ProgressEvent[DynamoDBTableProperties]:
        """
        Update a resource

        IAM permissions required:
          - dynamodb:UpdateTable
          - dynamodb:DescribeTable
          - dynamodb:DescribeTimeToLive
          - dynamodb:UpdateTimeToLive
          - dynamodb:UpdateContinuousBackups
          - dynamodb:UpdateContributorInsights
          - dynamodb:DescribeContinuousBackups
          - dynamodb:DescribeKinesisStreamingDestination
          - dynamodb:ListTagsOfResource
          - dynamodb:TagResource
          - dynamodb:UntagResource
          - dynamodb:DescribeContributorInsights
          - dynamodb:EnableKinesisStreamingDestination
          - dynamodb:DisableKinesisStreamingDestination
          - kinesis:DescribeStream
          - kinesis:PutRecords
          - iam:CreateServiceLinkedRole
          - kms:CreateGrant
          - kms:Describe*
          - kms:Get*
          - kms:List*
          - kms:RevokeGrant
        """
        raise NotImplementedError


class DynamoDBTableProviderPlugin(CloudFormationResourceProviderPlugin):
    name = "AWS::DynamoDB::Table"

    def __init__(self):
        self.factory: Optional[Type[ResourceProvider]] = None

    def load(self):
        self.factory = DynamoDBTableProvider
