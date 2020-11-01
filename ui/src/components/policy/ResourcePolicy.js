import React, { useState } from "react";
import { Header, Icon, Message, Segment, Tab } from "semantic-ui-react";
import Issues from "./Issues";
import Tags from "./Tags";
import { usePolicyContext } from "./hooks/PolicyProvider";
import { PolicyMonacoEditor } from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";

const ResourcePolicy = () => {
  const { resource = {}, handleResourcePolicySubmit } = usePolicyContext();
  const { s3_errors = {}, resource_details = {} } = resource;

  const tabs = [
    {
      menuItem: {
        key: "policy",
        content: "Resource Policy",
      },
      render: () => {
        return (
          <Tab.Pane>
            <>
              <Header as="h2">
                Resource Policy
                <Header.Subheader>
                  You can add/edit/delete resource policy here.
                </Header.Subheader>
              </Header>
              <Message warning attached="top">
                <Icon name="warning" />
                Double check whether cross account access for this resource is
                necessary.
              </Message>
              <Segment
                attached
                style={{
                  border: 0,
                  padding: 0,
                }}
              >
                <PolicyMonacoEditor
                  policy={{
                    PolicyName: "Resource Policy",
                    PolicyDocument: resource_details.Policy,
                  }}
                />
              </Segment>
            </>
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
            <Tags tags={resource_details.TagSet} />
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
            <Issues s3={s3_errors} />
          </Tab.Pane>
        );
      },
    },
  ];

  return (
    <>
      <Tab panes={tabs} />
      <JustificationModal handleSubmit={handleResourcePolicySubmit} />
    </>
  );
};

export default ResourcePolicy;
