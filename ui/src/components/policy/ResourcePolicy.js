import React from "react";
import { Tab } from "semantic-ui-react";
import Issues from "./Issues";
import ResourcePolicyEditor from "./ResourcePolicyEditor";
import Tags from "./Tags";

const ResourcePolicy = () => {
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
    {
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
    },
  ];

  return (
    <>
      <Tab panes={tabs} />
    </>
  );
};

export default ResourcePolicy;
