import React, { useEffect, useState } from "react";
import { Button, Icon, Header, Message, Segment } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";
import { PolicyMonacoEditor } from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";

const AssumeRolePolicy = () => {
  const { resource = {} } = usePolicyContext();

  const { assume_role_policy_document } = resource;
  const [assumeRolePolicy] = useState({
    PolicyName: "Assume Role Policy Document",
    PolicyDocument: assume_role_policy_document,
  });

  return (
    <>
      <Header as="h2">
        Assume Role Policy Document
        <Header.Subheader>
          You can modify this role's assume role policy here.
        </Header.Subheader>
      </Header>
      <Message warning attached="top">
        <Icon name="warning" />
        Other roles that need to assume this role must have an
        <a
          href={
            "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_enable-create.html"
          }
          target={"_blank"}
        >
          {" "}
          sts:AssumeRole
        </a>{" "}
        allowance for this role.
      </Message>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        <PolicyMonacoEditor
          policy={assumeRolePolicy}
          policyType={"assume_role_policy"}
        />
      </Segment>
      <JustificationModal />
    </>
  );
};

export default AssumeRolePolicy;
