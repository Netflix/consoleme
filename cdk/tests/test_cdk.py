import pytest

from cdk.app import app


@pytest.fixture(scope="module")
def consoleme_cf_template():
    return app.synth().get_stack("ConsoleMeECS").template


@pytest.fixture(scope="module")
def spoke_cf_template():
    return app.synth().get_stack("ConsoleMeSpoke").template


def test_consoleme_count_nested_stacks(consoleme_cf_template):
    assert (
        len(
            [
                resource
                for resource in consoleme_cf_template["Resources"]
                if consoleme_cf_template["Resources"][resource]["Type"]
                == "AWS::CloudFormation::Stack"
            ]
        )
        == 10
    )


def test_spoke_count_iam_roles(spoke_cf_template):
    assert (
        len(
            [
                resource
                for resource in spoke_cf_template["Resources"]
                if spoke_cf_template["Resources"][resource]["Type"] == "AWS::IAM::Role"
            ]
        )
        == 1
    )


def test_spoke_count_iam_policies(spoke_cf_template):
    assert (
        len(
            [
                resource
                for resource in spoke_cf_template["Resources"]
                if spoke_cf_template["Resources"][resource]["Type"]
                == "AWS::IAM::Policy"
            ]
        )
        == 1
    )
