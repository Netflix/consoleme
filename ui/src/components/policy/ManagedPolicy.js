import React, { useEffect, useState } from "react";
import {
  Button,
  Dropdown,
  Form,
  List,
  Icon,
  Header,
  Segment,
} from "semantic-ui-react";
import { sendRequestCommon } from "../../helpers/utils";

const ManagedPolicy = ({ policies = [], arn = "" }) => {
  const [managedPolicies, setManagedPolicies] = useState([]);
  const [managedPolicyOptions, setManagedPolicyOptions] = useState([]);
  const [isAdminUser, setIsAdminUser] = useState(false);

  // Fetch managed policies for account
  useEffect(() => {
    async function populateData() {
      if (arn) {
        await setManagedPolicies(
          await sendRequestCommon(
            null,
            "/api/v2/managed_policies/" + arn.split(":")[4],
            "get"
          )
        );
      }
    }

    populateData();
  }, [arn]); //eslint-disable-line

  // Update dropdown option list
  useEffect(() => {
    setManagedPolicyOptions(
      managedPolicies.map((value, i) => ({
        key: value,
        value: value,
        text: value,
      }))
    );
  }, [managedPolicies]);

  const handleManagePolicySelect = async (e, { value }) => {
    // TODO: heewonk - Handle Justification Modal and response
    console.log(e);
    const requestV2 = {
      justification: "Justification is unhandled right now",
      admin_auto_approve: isAdminUser,
      changes: {
        changes: [
          {
            principal_arn: arn,
            arn: value,
            change_type: "managed_policy",
            action: "attach",
          },
        ],
      },
    };
    const response = await sendRequestCommon(requestV2, "/api/v2/request");
    console.log(response);

    // Valid response:
    //     {
    //   "errors": 0,
    //   "request_created": true,
    //   "request_id": "0c674259-7a00-4ab4-bc7d-511759b58de7",
    //   "request_url": "/policies/request/0c674259-7a00-4ab4-bc7d-511759b58de7",
    //   "action_results": []
    // }

    // Valid Response #2 Admin autoapprove:
    //     {
    //   "errors": 0,
    //   "request_created": true,
    //   "request_id": "cd7d6055-e8b7-48df-914b-549cf33c00b2",
    //   "request_url": "/policies/request/cd7d6055-e8b7-48df-914b-549cf33c00b2",
    //   "action_results": [
    //     {
    //       "status": "success",
    //       "message": "Successfully attached managed policy arn:aws:iam::aws:policy/AWSIoT1ClickReadOnlyAccess to role: consoleme_oss_2_test_admin",
    //       "visible": true
    //     }
    //   ]
    // }
  };

  const handleManagePolicyDelete = async (e) => {
    // TODO: heewonk - Handle Justification Modal and response
    const requestV2 = {
      justification: "Justification is unhandled right now",
      admin_auto_approve: isAdminUser,
      changes: {
        changes: [
          {
            principal_arn: arn,
            arn: e.target.name,
            change_type: "managed_policy",
            action: "detach",
          },
        ],
      },
    };
    const response = await sendRequestCommon(requestV2, "/api/v2/request");
    console.log(response);
    // Valid Response #1  Normal request:
    //     {
    //   "errors": 0,
    //   "request_created": true,
    //   "request_id": "38a7ab03-51c7-454b-909f-24c9cbb2353b",
    //   "request_url": "/policies/request/38a7ab03-51c7-454b-909f-24c9cbb2353b",
    //   "action_results": []
    // }

    // Valid Response #2 Admin AutoApprove:
    //     {
    //   "errors": 0,
    //   "request_created": true,
    //   "request_id": "43e844ed-af21-4492-a0b5-d426f3b3d0e7",
    //   "request_url": "/policies/request/43e844ed-af21-4492-a0b5-d426f3b3d0e7",
    //   "action_results": [
    //     {
    //       "status": "success",
    //       "message": "Successfully detached managed policy arn:aws:iam::aws:policy/AWSMarketplaceFullAccess from role: consoleme_oss_2_test_admin",
    //       "visible": true
    //     }
    //   ]
    // }
  };

  return (
    <>
      <Header as="h2">Managed Policies</Header>
      <Form>
        <Form.Field>
          <label>
            Select a managed policy from the dropdown that you wish to add to
            this role.
          </label>
          <Dropdown
            placeholder="Choose a managed policy to add to this role."
            fluid
            search
            selection
            options={managedPolicyOptions}
            onChange={handleManagePolicySelect}
          />
        </Form.Field>
      </Form>
      <Header as="h3" attached="top" content="Attached Policies" />
      <Segment attached="bottom">
        <List divided size="medium" relaxed="very" verticalAlign="middle">
          {policies.map((policy) => {
            return (
              <List.Item key={policy.PolicyName}>
                <List.Content floated="right">
                  <Button
                    negative
                    size="small"
                    name={policy.PolicyArn}
                    onClick={handleManagePolicyDelete}
                  >
                    <Icon name="remove" />
                    Remove
                  </Button>
                </List.Content>
                <List.Content>
                  <List.Header>{policy.PolicyName}</List.Header>
                  <List.Description as="a">{policy.PolicyArn}</List.Description>
                </List.Content>
              </List.Item>
            );
          })}
        </List>
      </Segment>
    </>
  );
};

export default ManagedPolicy;
