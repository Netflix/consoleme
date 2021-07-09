import React from "react";
import { Label, Tab } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";
import AssumeRolePolicy from "./AssumeRolePolicy";
import ManagedPolicy from "./ManagedPolicy";
import PermissionsBoundary from "./PermissionsBoundary";
import ServiceControlPolicy from "./ServiceControlPolicy";
import InlinePolicy from "./InlinePolicy";
import Issues from "./Issues";
import Tags from "./Tags";

const IAMRolePolicy = () => {
  const { resource = {} } = usePolicyContext();

  const {
    cloudtrail_details = {},
    inline_policies = [],
    s3_details = {},
    assume_role_policy_document = null,
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
  ];
  if (assume_role_policy_document) {
    tabs.push({
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
    });
  }
  tabs.push.apply(tabs, [
    {
      menuItem: {
        key: "managed_policy",
        content: (() => {
          return (
            <>
              Managed Policies
              <Label>{resource?.managed_policies?.length}</Label>
            </>
          );
        })(),
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
        key: "permissions_boundary",
        content: (() => {
          return (
            <>
              Permissions Boundary
              <Label>
                {(resource?.permissions_boundary &&
                  Object.keys(resource.permissions_boundary).length) !== 0
                  ? "Attached"
                  : "Detached"}
              </Label>
            </>
          );
        })(),
      },
      render: () => {
        return (
          <Tab.Pane>
            <PermissionsBoundary />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: {
        key: "service_control_policy",
        content: <>Service Control Policies</>,
      },
      render: () => {
        return (
          <Tab.Pane>
            <ServiceControlPolicy />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: {
        key: "tags",
        content: (() => {
          return (
            <>
              Tags
              <Label>{resource?.tags?.length}</Label>
            </>
          );
        })(),
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
  ]);

  return (
    <Tab
      menu={{ fluid: true, vertical: true, tabular: true }}
      panes={tabs}
      className="vertical-tab-override"
    />
  );
};

export default IAMRolePolicy;
