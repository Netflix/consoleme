import React from "react";
import { Label, Tab } from "semantic-ui-react";
import AssumeRolePolicy from "./AssumeRolePolicy";
import ManagedPolicy from "./ManagedPolicy";
import InlinePolicy from "./InlinePolicy";
import Issues from "./Issues";
import Tags from "./Tags";

const IAMRolePolicy = ({ resource }) => {
  const {
    arn = "",
    assume_role_policy_document = {},
    cloudtrail_details = {},
    inline_policies = [],
    managed_policies = [],
    s3_details = {},
    tags = [],
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
            <InlinePolicy
              arn={arn}
              policies={inline_policies}
            />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: "Assume Role Policy",
      render: () => {
        return (
          <Tab.Pane>
            <AssumeRolePolicy
              policies={assume_role_policy_document}
              arn={arn}
            />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: "Managed Policy",
      render: () => {
        return (
          <Tab.Pane>
            <ManagedPolicy policies={managed_policies} arn={arn} />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: "Tags",
      render: () => {
        return (
          <Tab.Pane>
            <Tags tags={tags} />
          </Tab.Pane>
        );
      },
    },
    {
      menuItem: {
        key: "issues",
        content: (() => {
          const cloudtrail_details_errors =
            cloudtrail_details && cloudtrail_details.errors;
          const s3_details_errors = s3_details && s3_details.errors;

          if (cloudtrail_details_errors && s3_details_errors) {
            return (
              <>
                Issues
                <Label color="red">
                  {cloudtrail_details_errors.cloudtrail_errors.length +
                    s3_details_errors.s3_errors.length}
                </Label>
              </>
            );
          } else {
            return "Issues";
          }
        })(),
      },
      render: () => {
        return (
          <Tab.Pane>
            <Issues cloudtrail={cloudtrail_details} s3={s3_details} />
          </Tab.Pane>
        );
      },
    },
  ];

  return <Tab panes={tabs} />;
};

export default IAMRolePolicy;
