import React from "react";
import { Accordion, Button, Header, Segment } from "semantic-ui-react";
import { Link } from "react-router-dom";

import { usePolicyContext } from "./hooks/PolicyProvider";
import {
  PolicyMonacoEditor,
  NewPolicyMonacoEditor,
} from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";

const InlinePolicy = () => {
  const {
    activeIndex = [],
    inlinePolicies = [],
    isNewPolicy = false,
    resource = {},
    setActiveIndex,
    setIsNewPolicy,
    setPolicyType,
  } = usePolicyContext();

  const addInlinePolicy = () => {
    setIsNewPolicy(true);
  };

  const onTitleClick = (e, { index }) => {
    if (activeIndex.includes(index)) {
      setActiveIndex(activeIndex.filter((i) => i !== index));
    } else {
      setActiveIndex([...activeIndex, index]);
    }
  };

  const panels = inlinePolicies.map((policy) => {
    return {
      key: policy.PolicyName,
      title: policy.PolicyName,
      content: {
        content: (
          <PolicyMonacoEditor policy={policy} policyType={"inline_policy"} />
        ),
      },
    };
  });

  if (isNewPolicy) {
    panels.unshift({
      key: "new_policy",
      title: "New Policy",
      content: {
        content: <NewPolicyMonacoEditor policyType={"inline_policy"} />,
      },
    });
  }

  return (
    <>
      <Segment
        basic
        clearing
        style={{
          padding: 0,
        }}
      >
        <Header as="h2" floated="left">
          Inline Policies
          <Header.Subheader>
            You can add/edit/delete inline policies for this role from here.
            Please create a new policy by using the buttons on the right.
          </Header.Subheader>
        </Header>
        <Button.Group floated="right">
          <Button onClick={addInlinePolicy} positive>
            Create New Inline Policy
          </Button>
          <Button.Or />
          <Button
            as={Link}
            disabled={false}
            to={`/ui/selfservice?arn=${encodeURIComponent(resource.arn)}`}
            primary
          >
            Policy Wizard
          </Button>
        </Button.Group>
      </Segment>
      <Accordion
        activeIndex={activeIndex}
        exclusive={false}
        fluid
        onTitleClick={onTitleClick}
        panels={panels}
        styled
      />
      <JustificationModal />
    </>
  );
};

export default InlinePolicy;
