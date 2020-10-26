import React, { useEffect, useState } from "react";
import { Accordion, Button, Header, Segment } from "semantic-ui-react";
import { Link } from "react-router-dom";
import {
  PolicyMonacoEditor,
  NewPolicyMonacoEditor,
} from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";
import { useInlinePolicy } from "../../hooks/usePolicy";

const InlinePolicy = ({ arn = "", policies = [] }) => {
  const {
    currentPolicies,
    newPolicy,
    addPolicy,
    removePolicy,
    setAdminAutoApprove,
    justification,
    setJustification,
    updatePolicy,
    deletePolicy,
    handlePolicySubmit,
  } = useInlinePolicy({ arn, policies });

  const [activeIndex, setActiveIndex] = useState([]);
  const [isNewPolicy, setIsNewPolicy] = useState(false);
  const [openJustification, setOpenJustification] = useState(false);

  const addInlinePolicy = () => {
    setIsNewPolicy(true);
  };

  const cancelInlinePolicy = () => {
    // TODO, do more clean up
    setIsNewPolicy(false);
  };

  const onTitleClick = (e, { index }) => {
    if (activeIndex.includes(index)) {
      setActiveIndex(activeIndex.filter((i) => i !== index));
    } else {
      setActiveIndex([...activeIndex, index]);
    }
  };

  useEffect(() => {
    setActiveIndex([...Array(currentPolicies.length).keys()]);
  }, [currentPolicies]);

  const panels = currentPolicies.map((policy) => {
    return {
      key: policy.PolicyName,
      title: policy.PolicyName,
      content: {
        content: (
          <PolicyMonacoEditor
            policy={policy}
            setAdminAutoApprove={setAdminAutoApprove}
            updatePolicy={updatePolicy}
            deletePolicy={deletePolicy}
            setOpenJustification={setOpenJustification}
          />
        ),
      },
    };
  });

  if (isNewPolicy) {
    panels.unshift({
      key: "new_policy",
      title: "New Policy",
      content: {
        content: (
          <NewPolicyMonacoEditor
            policy={newPolicy}
            setAdminAutoApprove={setAdminAutoApprove}
            setNewPolicy={addPolicy}
            cancelInlinePolicy={cancelInlinePolicy}
            setOpenJustification={setOpenJustification}
          />
        ),
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
            to={`/ui/selfservice?arn=${encodeURIComponent(arn)}`}
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
      <JustificationModal
        justification={justification}
        setJustification={setJustification}
        openJustification={openJustification}
        setOpenJustification={setOpenJustification}
        removePolicy={removePolicy}
        handleSubmit={handlePolicySubmit}
      />
    </>
  );
};

export default InlinePolicy;
