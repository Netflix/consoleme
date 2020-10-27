import React, { useEffect, useState } from "react";
import { Button, Icon, Header, Message, Segment } from "semantic-ui-react";
import MonacoEditor from "react-monaco-editor";
import { sendRequestCommon } from "../../helpers/utils";
import { usePolicyContext } from "./hooks/PolicyProvider";

const editorOptions = {
  selectOnLineNumbers: true,
  quickSuggestions: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false,
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
};

const AssumeRolePolicy = () => {
  const {
    resource = {},
    adminAutoApprove,
    setAdminAutoApprove,
  } = usePolicyContext();
  const { arn, assume_role_policy_document } = resource;
  const [assumeRolePolicy, setAssumeRolePolicy] = useState("");

  const onEditChange = (e, d) => {
    try {
      setAssumeRolePolicy(JSON.parse(e));
    } catch {}
  };
  const handleAssumeRolePolicyAdminSave = async () => {
    setAdminAutoApprove(true);
    await handleAssumeRolePolicySubmit();
  };

  const handleAssumeRolePolicySubmit = async () => {
    if (!assumeRolePolicy) {
      // TODO: Show error to end-user
      console.log("Assume role policy hasn't changed");
      return;
    }
    // TODO: heewonk - Handle Justification Modal and response
    // When page refreshes is it possible to go to the tab the user was last at?
    const requestV2 = {
      justification: "Justification is unhandled right now",
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal_arn: arn,
            change_type: "assume_role_policy",
            policy: {
              policy_document: assumeRolePolicy,
            },
          },
        ],
      },
    };

    const response = await sendRequestCommon(requestV2, "/api/v2/request");

    // EXAMPLE RESPONSE:
    // {"errors": 0, "request_created": true, "request_id": "63478ecd-37ac-490b-a87f-8194e52dbc40", "request_url": "/policies/request/63478ecd-37ac-490b-a87f-8194e52dbc40", "action_results": []}
    // EXAMPLE RESPONSE 2:
    //     {
    //   "errors": 0,
    //   "request_created": true,
    //   "request_id": "a05af846-3d3d-42ea-9065-208b5cc27286",
    //   "request_url": "/policies/request/a05af846-3d3d-42ea-9065-208b5cc27286",
    //   "action_results": [
    //     {
    //       "status": "success",
    //       "message": "Successfully updated assume role policy policy for role: consoleme_oss_2_test_admin",
    //       "visible": true
    //     }
    //   ]
    // }
  };

  return (
    <>
      <Header as="h2">
        Assume Role Policy Document
        <Header.Subheader>
          You can add/edit/delete assume role policy for this role from here.
        </Header.Subheader>
      </Header>
      <Message warning attached="top">
        <Icon name="warning" />
        Make sure the roles that assume this role are carefully reviewed and
        have sts:assumerole permission.
      </Message>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <MonacoEditor
          height="540px"
          language="json"
          theme="vs-dark"
          defaultValue={JSON.stringify(assume_role_policy_document, null, "\t")}
          onChange={onEditChange}
          options={editorOptions}
          textAlign="center"
        />
      </Segment>
      <Button.Group attached="bottom">
        <Button
          positive
          icon="save"
          content="Save"
          onClick={handleAssumeRolePolicyAdminSave}
        />
        <Button.Or />
        <Button
          primary
          icon="send"
          content="Submit"
          onClick={handleAssumeRolePolicySubmit}
        />
      </Button.Group>
    </>
  );
};

export default AssumeRolePolicy;
