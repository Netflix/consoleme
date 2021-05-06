import React, { useEffect, useRef, useState } from "react";
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
import usePermissionsBoundary from "./hooks/usePermissionsBoundary";
import { JustificationModal } from "./PolicyModals";
import { useAuth } from "../../auth/AuthProviderDefault";
import MonacoEditor from "react-monaco-editor";

const PermissionsBoundary = () => {
  const { user, sendRequestCommon } = useAuth();
  const {
    accountID = "",
    permissionsBoundary = {},
    resource,
    addPermissionsBoundary,
    deletePermissionsBoundary,
    setModalWithAdminAutoApprove,
    handlePermissionsBoundarySubmit,
  } = usePermissionsBoundary();

  const [availableManagedPolicies, setAvailableManagedPolicies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [
    attachedPermissionsBoundaryDetails,
    setAttachedPermissionsBoundaryDetails,
  ] = useState(null);
  const editorRef = useRef();
  // available managed policies are only used for rendering. so let's retrieve from here.
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
      setAvailableManagedPolicies(result);
    })();
  }, [accountID, sendRequestCommon]);

  useEffect(() => {
    (async () => {
      const result = await sendRequestCommon(
        null,
        `/api/v2/managed_policies/${resource?.permissions_boundary?.PermissionsBoundaryArn}`,
        "get"
      );
      if (!result?.data) {
        return;
      }
      setAttachedPermissionsBoundaryDetails(result.data);
    })();
  }, [accountID, resource, sendRequestCommon]);

  const onPermissionsBoundaryChange = (e, { value }) => {
    addPermissionsBoundary(value);
    setSelected(value);
  };
  const onPermissionsBoundarySave = () => setModalWithAdminAutoApprove(true);
  const onPermissionsBoundarySubmit = () => setModalWithAdminAutoApprove(false);
  const onPermissionsBoundaryDelete = (arn) => {
    deletePermissionsBoundary(arn);
    setModalWithAdminAutoApprove(true);
  };
  const onPermissionsBoundaryDeleteRequest = (arn) => {
    deletePermissionsBoundary(arn);
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

  const editorOptions = {
    readOnly: true,
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
      alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
  };

  return (
    <>
      <Header as="h2">Permissions Boundary</Header>
      <Form>
        <Form.Field>
          <label>
            Select a managed policy from the dropdown that you wish to add to
            this role as a permissions boundary.
          </label>
          <Dropdown
            placeholder="Choose a managed policy to use as a permissions boundary."
            fluid
            search
            selection
            options={options}
            onChange={onPermissionsBoundaryChange}
          />
          <ButtonGroup attached="bottom">
            {user?.authorization?.can_edit_policies ? (
              <>
                <Button
                  positive
                  icon="save"
                  content="Add"
                  onClick={onPermissionsBoundarySave}
                  disabled={!selected}
                />
                <ButtonOr />
              </>
            ) : null}
            <Button
              primary
              icon="send"
              content="Request"
              onClick={onPermissionsBoundarySubmit}
              disabled={!selected}
            />
          </ButtonGroup>
        </Form.Field>
      </Form>
      <Header as="h3" attached="top" content="Attached Permissions Boundary" />
      <Segment attached="bottom">
        <List divided size="medium" relaxed="very" verticalAlign="middle">
          <List.Item key={permissionsBoundary?.PolicyName}>
            <List.Content floated="right">
              <Button.Group attached="bottom">
                {user?.authorization?.can_edit_policies ? (
                  <>
                    <Button
                      negative
                      size="small"
                      name={permissionsBoundary?.PermissionsBoundaryArn}
                      onClick={() =>
                        onPermissionsBoundaryDelete(
                          permissionsBoundary.PermissionsBoundaryArn
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
                  name={permissionsBoundary?.PermissionsBoundaryArn}
                  onClick={() =>
                    onPermissionsBoundaryDeleteRequest(
                      permissionsBoundary?.PermissionsBoundaryArn
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
                {permissionsBoundary?.PermissionsBoundaryArn?.split("/").slice(
                  -1
                )}
              </List.Header>
              <List.Description as="a">
                {permissionsBoundary?.PermissionsBoundaryArn}
              </List.Description>
              {attachedPermissionsBoundaryDetails &&
              attachedPermissionsBoundaryDetails ? (
                <Segment
                  attached
                  style={{
                    border: 10,
                    padding: 10,
                  }}
                >
                  <MonacoEditor
                    ref={editorRef}
                    height="540px"
                    language="json"
                    theme="vs-dark"
                    value={JSON.stringify(
                      attachedPermissionsBoundaryDetails,
                      null,
                      "\t"
                    )}
                    options={editorOptions}
                    textAlign="center"
                  />
                </Segment>
              ) : null}
            </List.Content>
          </List.Item>
        </List>
      </Segment>
      <JustificationModal handleSubmit={handlePermissionsBoundarySubmit} />
    </>
  );
};

export default PermissionsBoundary;
