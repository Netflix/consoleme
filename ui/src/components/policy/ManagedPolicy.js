import React, { useEffect, useState } from "react";
import {
  Button,
  Dropdown,
  Form,
  List,
  Icon,
  Header,
  Segment,
  ButtonGroup,
  ButtonOr,
} from "semantic-ui-react";
import useManagedPolicy from "./hooks/useManagedPolicy";
import { JustificationModal } from "./PolicyModals";
import { sendRequestCommon } from "../../helpers/utils";
import { useAuth } from "../../auth/AuthProvider";

const ManagedPolicy = () => {
  const { user } = useAuth();
  const {
    accountID = "",
    managedPolicies = [],
    addManagedPolicy,
    deleteManagedPolicy,
    setModalWithAdminAutoApprove,
    handleManagedPolicySubmit,
  } = useManagedPolicy();

  const [availableManagedPolicies, setAvailableManagedPolicies] = useState([]);
  const [selected, setSelected] = useState(null);

  // available managed policies are only used for rendering. so let's retrieve from here.
  useEffect(() => {
    (async () => {
      const result = await sendRequestCommon(
        null,
        `/api/v2/managed_policies/${accountID}`,
        "get"
      );
      setAvailableManagedPolicies(result);
    })();
  }, []);

  const onManagePolicyChange = (e, { value }) => {
    addManagedPolicy(value);
    setSelected(value);
  };
  const onManagedPolicySave = () => setModalWithAdminAutoApprove(true);
  const onManagedPolicySubmit = () => setModalWithAdminAutoApprove(false);
  const onManagePolicyDelete = (arn) => {
    deleteManagedPolicy(arn);
    setModalWithAdminAutoApprove(true);
  };
  const onManagePolicyDeleteRequest = (arn) => {
    deleteManagedPolicy(arn);
    setModalWithAdminAutoApprove(false);
  };

  const options =
    availableManagedPolicies &&
    availableManagedPolicies.map((policy) => {
      return {
        key: policy,
        value: policy,
        text: policy,
      };
    });

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
            options={options}
            onChange={onManagePolicyChange}
          />
          <ButtonGroup attached="bottom">
            {user?.authorization?.can_edit_policies ? (
              <>
                <Button
                  positive
                  icon="save"
                  content="Add"
                  onClick={onManagedPolicySave}
                  disabled={!selected}
                />
                <ButtonOr />
              </>
            ) : null}
            <Button
              primary
              icon="send"
              content="Request"
              onClick={onManagedPolicySubmit}
              disabled={!selected}
            />
          </ButtonGroup>
        </Form.Field>
      </Form>
      <Header as="h3" attached="top" content="Attached Policies" />
      <Segment attached="bottom">
        <List divided size="medium" relaxed="very" verticalAlign="middle">
          {managedPolicies.map((policy) => {
            return (
              <List.Item key={policy.PolicyName}>
                <List.Content floated="right">
                  <Button.Group attached="bottom">
                    {user?.authorization?.can_edit_policies ? (
                      <>
                        <Button
                          negative
                          size="small"
                          name={policy.PolicyArn}
                          onClick={() => onManagePolicyDelete(policy.PolicyArn)}
                        >
                          <Icon name="remove" />
                          Remove
                        </Button>
                        <Button.Or />
                      </>
                    ) : null}
                    <Button
                      negative
                      size="small"
                      name={policy.PolicyArn}
                      onClick={() =>
                        onManagePolicyDeleteRequest(policy.PolicyArn)
                      }
                    >
                      <Icon name="remove" />
                      Request Removal
                    </Button>
                  </Button.Group>
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
      <JustificationModal handleSubmit={handleManagedPolicySubmit} />
    </>
  );
};

export default ManagedPolicy;
