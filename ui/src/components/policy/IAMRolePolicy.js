import React from "react";
import { Label, Tab } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";
import AssumeRolePolicy from "./AssumeRolePolicy";
import ManagedPolicy from "./ManagedPolicy";
import InlinePolicy from "./InlinePolicy";
import Issues from "./Issues";
import Tags from "./Tags";

const IAMRolePolicy = () => {
  const { resource = {} } = usePolicyContext();

  const {
    cloudtrail_details = {},
    inline_policies = [],
    s3_details = {},
  } = resource;

  const tabs = [
    {
      menuItem: {
        key: "inline_policy",
        content: (
          <>
            Inline Policy
            <Label>{inline_policies.length}</Label>
          </>
        ),
      },
      render: () => {
        return (
          <Tab.Pane>
            <InlinePolicy />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: {
        key: "assume_role_policy",
        content: "Assume Role Policy",
      },
      render: () => {
        return (
          <Tab.Pane>
            <AssumeRolePolicy />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: {
        key: "managed_policy",
        content: "Managed Policy",
      },
      render: () => {
        return (
          <Tab.Pane>
            <ManagedPolicy />
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
          if (cloudtrail_details?.errors || s3_details?.errors) {
            return (
              <>
                Issues
                <Label color="red">
                  {cloudtrail_details?.errors?.cloudtrail_errors.length +
                    s3_details?.errors?.s3_errors.length}
                </Label>
              </>
            );
          }
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

  return <Tab panes={tabs} />;
};

export default IAMRolePolicy;
