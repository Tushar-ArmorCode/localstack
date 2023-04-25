import pytest

from localstack.utils.strings import short_uid

TEMPLATE = """
Parameters:
    ResName:
        Type: String
    TagValue:
        Type: String
Resources:
    MyBucket:
        Type: AWS::SNS::Topic
        Properties:
            TopicName: !Ref ResName
            Tags:
                - Key: CustomTag
                  Value: !Ref TagValue
"""


# CreateStack does it fail synchronously when trying to resolve an SSM parameter but it isn't allowed to
# CreateStack - point CFn parameter to an SSM parameter that doesn't exist
# CreateStack - Create a resource that cfn / (or the role) doesn't have access for

# CreateStack - Upload a syntactically wrong template (valid JSON/YAML)
# CreateStack - Upload a syntactically wrong template (invalid JSON/YAML)
# CreateStack - Upload template with missing parameter
# CreateStack - Upload template with a resource having missing fields
# CreateStack - Upload template with a resource having an unspec'ed field

# CreateStack - Upload template with a failure caused by an invalid usage of an intrinsic function
# CreateStack - Ref something that doesn't exist
# CreateStack - Importing non-existing exports

# need more setup (can be done later)
# CreateStack - Create with a failing global transformation
# CreateStack - Missing item in mapping
# CreateStack - Rules (passing / non-passing)

create_args = {
    "resolve_ssm_parameter_as_stack_parameter_permission_denied": {
        "TemplateBody": TEMPLATE,
        "Parameters": [
            {"ParameterKey": "TagValue", "ParameterValue": "tag1"},
        ],
    }
}


@pytest.mark.parametrize(
    "scenario",
    [
        "resolve_ssm_parameter_as_stack_parameter_permission_denied",
        "resolve_ssm_parameter_as_stack_parameter_does_not_exist",
        "create_resource_permission_denied",

        "template_invalid_cfn_schema",
        "template_invalid_yaml_syntax",
        "missing_required_parameter",


        "missing_field_in_resource_properties",
        "additional_field_in_resource_properties_not_in_schema",
        "invalid_intrinsic_function_usage",

        "ref_nonexisting",
        "import_nonexisting_export",

        "missing_item_in_mapping",
        "passing_rule",
        "failing_rule",

        # optional
        # "invalid_global_transformation",
    ]
)
def test_skeleton_changeset(aws_client, snapshot, cleanups, scenario):
    cfn_client = aws_client.cloudformation
    stack_name = f"cfnv2-test-stack-{short_uid()}"
    change_set_name = f"cfnv2-test-changeset-{short_uid()}"

    change_set_result = cfn_client.create_change_set(
        StackName=stack_name,
        ChangeSetName=change_set_name,
        ChangeSetType="CREATE",
        **create_args[scenario]

    )
    change_set_arn = change_set_result['Id']
    stack_arn = change_set_result['StackId']
    cleanups.append(lambda: cfn_client.delete_stack(StackName=stack_arn))

    describe_stack = cfn_client.describe_stacks(StackName=stack_arn)
    snapshot.match("describe_stack", describe_stack)
    describe_changeset_byarnalone = cfn_client.describe_change_set(ChangeSetName=change_set_arn)
    snapshot.match("describe_changeset_byarnalone", describe_changeset_byarnalone)
    cfn_client.get_waiter("change_set_create_complete").wait(ChangeSetName=change_set_arn)
    describe_changeset_bynames_postwait = cfn_client.describe_change_set(ChangeSetName=change_set_name, StackName=stack_name)
    snapshot.match("describe_changeset_bynames_postwait", describe_changeset_bynames_postwait)

    # execute changeset
    try:
        cfn_client.execute_change_set(ChangeSetName=change_set_arn)
        cfn_client.get_waiter("stack_create_complete").wait(StackName=stack_arn)

        # capture post-state
        describe_stack_postexecute = cfn_client.describe_stacks(StackName=stack_arn)
        snapshot.match("describe_stack_postexecute", describe_stack_postexecute)
        postcreate_original_template = cfn_client.get_template(StackName=stack_name, ChangeSetName=change_set_name, TemplateStage="Original")
        snapshot.match("postcreate_original_template", postcreate_original_template)
        postcreate_processed_template = cfn_client.get_template(StackName=stack_name, ChangeSetName=change_set_name, TemplateStage="Processed")
        snapshot.match("postcreate_processed_template", postcreate_processed_template)
    except Exception as e:
        snapshot.match("execute_change_set_exc", e.value.response)
