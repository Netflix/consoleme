import React, { useEffect, useState } from "react";
import { Accordion, Button, Header, Segment } from "semantic-ui-react";
import { Link } from "react-router-dom";
import useInlinePolicy from "./hooks/useInlinePolicy";
import {
  PolicyMonacoEditor,
  NewPolicyMonacoEditor,
} from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";

const InlinePolicy = () => {
  const {
    arn,
    isNewPolicy = false,
    inlinePolicies = [],
    addInlinePolicy,
    updateInlinePolicy,
    deleteInlinePolicy,
    setIsNewPolicy,
    handleInlinePolicySubmit,
  } = useInlinePolicy();

  const [activeIndex, setActiveIndex] = useState([]);
  const [panels, setPanels] = useState([]);

  const toggleNewInlinePolicy = () => {
    setIsNewPolicy(true);
  };

  const onTitleClick = (e, { index }) => {
    if (activeIndex.includes(index)) {
      setActiveIndex(activeIndex.filter((i) => i !== index));
    } else {
      setActiveIndex([...activeIndex, index]);
    }
  };

  useEffect(() => {
    if (!isNewPolicy) {
      setPanels((panels) => {
        return [...panels.filter((panel) => panel.key !== "new_policy")];
      });
      return;
    }
    setPanels((panels) => {
      setActiveIndex([...Array(panels.length + 1).keys()]);
      return [
        {
          key: "new_policy",
          title: "New Policy",
          content: {
            content: (
              <NewPolicyMonacoEditor
                addPolicy={addInlinePolicy}
                setIsNewPolicy={setIsNewPolicy}
              />
            ),
          },
        },
        ...panels,
      ];
    });
  }, [isNewPolicy, addInlinePolicy, setIsNewPolicy]);

  useEffect(() => {
    const newPanels = inlinePolicies.map((policy) => {
      return {
        key: policy.PolicyName,
        title: policy.PolicyName,
        content: {
          content: (
            <PolicyMonacoEditor
              context="inline_policy"
              policy={policy}
              deletePolicy={deleteInlinePolicy}
              updatePolicy={updateInlinePolicy}
            />
          ),
        },
      };
    });
    setPanels(newPanels);
    setActiveIndex([...Array(newPanels.length).keys()]);
  }, [inlinePolicies, deleteInlinePolicy, updateInlinePolicy]);

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
          <Button onClick={toggleNewInlinePolicy} positive>
            Create New Inline Policy
          </Button>
          <Button.Or />
          <Button
            as={Link}
            disabled={false}
            to={`/selfservice?arn=${encodeURIComponent(arn)}`}
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
      <JustificationModal handleSubmit={handleInlinePolicySubmit} />
    </>
  );
};

export default InlinePolicy;
