import React from "react";
import { Tab } from "semantic-ui-react";
import Issues from "./Issues";
import ResourcePolicyEditor from "./ResourcePolicyEditor";
import Tags from "./Tags";

const ResourcePolicy = (props) => {
  const serviceType = props.serviceType;
  const tabs = [
    {
      menuItem: {
        key: "resource_policy",
        content: "Resource Policy",
      },
      render: () => {
        return (
          <Tab.Pane>
            <ResourcePolicyEditor />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: {
        key: "tags",
        content: "Tags",
      },
      render: () => {
        return (
          <Tab.Pane>
            <Tags />
          </Tab.Pane>
        );
      },
    },
  ];

  // Only include Issues tab if resource type is eligible. IAM roles are handled by a different pane
  if (["s3"].includes(serviceType)) {
    tabs.push({
      menuItem: {
        key: "issues",
        content: (() => {
          return "Issues";
        })(),
      },
      render: () => {
        return (
          <Tab.Pane>
            <Issues />
          </Tab.Pane>
        );
      },
    });
  }

  return (
    <>
      <Tab panes={tabs} />
    </>
  );
};

export default ResourcePolicy;
