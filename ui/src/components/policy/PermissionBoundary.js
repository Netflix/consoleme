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
import { useAuth } from "../../auth/AuthProviderDefault";

const PermissionBoundary = () => {
  const { user, sendRequestCommon } = useAuth();
  const {
    accountID = "",
    permissionBoundary,
    addPermissionBoundary,
    removePermissionBoundary,
    setModalWithAdminAutoApprove,
    handlePermissionBoundarySubmit,
  } = useManagedPolicy();

  const [
    availablePermissionBoundaries,
    setAvailablePermissionBoundaries,
  ] = useState([]);
  const [selected, setSelected] = useState(null);

  // available permission boundaries are the same as managed policies
  useEffect(() => {
    (async () => {
      const result = await sendRequestCommon(
        null,
        `/api/v2/managed_policies/${accountID}`,
        "get"
      );
      if (!result) {
        return;
      }
      setAvailablePermissionBoundaries(result);
    })();
  }, [accountID, sendRequestCommon]);

  const onPermissionBoundaryChange = (e, { value }) => {
    addPermissionBoundary(value);
    setSelected(value);
  };
  const onPermissionBoundarySave = () => setModalWithAdminAutoApprove(true);
  const onPermissionBoundarySubmit = () => setModalWithAdminAutoApprove(false);
  const onPermissionBoundaryRemove = (arn) => {
    removePermissionBoundary(arn);
    setModalWithAdminAutoApprove(true);
  };
  const onPermissionBoundaryRemoveRequest = (arn) => {
    removePermissionBoundary(arn);
    setModalWithAdminAutoApprove(false);
  };

  const options =
    availablePermissionBoundaries &&
    availablePermissionBoundaries.map((policy) => {
      return {
        key: policy,
        value: policy,
        text: policy,
      };
    });

  return (
    <>
      <Header as="h2">Permission Boundary</Header>
      <Form>
        <Form.Field>
          <label>
            Select a permission boundary from the dropdown that you wish to add
            to this role.
          </label>
          <Dropdown
            placeholder="Choose a permission boundary to add to this role."
            fluid
            search
            selection
            options={options}
            onChange={onPermissionBoundaryChange}
          />
          <ButtonGroup attached="bottom">
            {user?.authorization?.can_edit_policies ? (
              <>
                <Button
                  positive
                  icon="save"
                  content={permissionBoundary ? "Replace" : "Add"}
                  onClick={onPermissionBoundarySave}
                  disabled={!selected}
                />
                <ButtonOr />
              </>
            ) : null}
            <Button
              primary
              icon="send"
              content={permissionBoundary ? "Request Replacement" : "Request"}
              onClick={onPermissionBoundarySubmit}
              disabled={!selected}
            />
          </ButtonGroup>
        </Form.Field>
      </Form>
      <Header as="h3" attached="top" content="Attached Permission Boundary" />
      <Segment attached="bottom">
        <List divided size="medium" relaxed="very" verticalAlign="middle">
          {permissionBoundary ? (
            <List.Item key={permissionBoundary.PermissionsBoundaryArn}>
              <List.Content floated="right">
                <Button.Group attached="bottom">
                  {user?.authorization?.can_edit_policies ? (
                    <>
                      <Button
                        negative
                        size="small"
                        name={permissionBoundary.PermissionsBoundaryArn}
                        onClick={() =>
                          onPermissionBoundaryRemove(
                            permissionBoundary.PermissionsBoundaryArn
                          )
                        }
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
                    name={permissionBoundary.PermissionsBoundaryArn}
                    onClick={() =>
                      onPermissionBoundaryRemoveRequest(
                        permissionBoundary.PermissionsBoundaryArn
                      )
                    }
                  >
                    <Icon name="remove" />
                    Request Removal
                  </Button>
                </Button.Group>
              </List.Content>
              <List.Content>
                <List.Header>
                  {permissionBoundary.PermissionsBoundaryArn}
                </List.Header>
              </List.Content>
            </List.Item>
          ) : null}
        </List>
      </Segment>
      <JustificationModal handleSubmit={handlePermissionBoundarySubmit} />
    </>
  );
};

export default PermissionBoundary;
