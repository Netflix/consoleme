import React from "react";
import { Header, Table } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";

const Issues = () => {
  const { resource = {} } = usePolicyContext();
  let s3 = null;
  let cloudtrail = null;
  let is_s3_resource = false;
  // This is where s3 errors stored for resource policy
  if (resource?.s3_errors) {
    is_s3_resource = true;
    s3 = {
      errors: {
        s3_errors: resource.s3_errors,
      },
    };
  } else {
    cloudtrail = resource.cloudtrail_details;
    s3 = resource.s3_details;
  }

  const cloudTrailErrors = () => {
    if (cloudtrail?.errors?.cloudtrail_errors.length > 0) {
      const rows = [];
      const header = (
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>Error Call</Table.HeaderCell>
            <Table.HeaderCell>Count</Table.HeaderCell>
          </Table.Row>
        </Table.Header>
      );

      cloudtrail.errors.cloudtrail_errors.forEach((error) => {
        rows.push(
          <Table.Row negative>
            <Table.Cell>{error.event_call}</Table.Cell>
            <Table.Cell>{error.count}</Table.Cell>
          </Table.Row>
        );
      });

      const errorLink = () => {
        if (cloudtrail?.error_url) {
          return (
            <>
              (
              <a
                href={cloudtrail.error_url}
                rel="noopener noreferrer"
                target="_blank"
              >
                Click here to see logs
              </a>
              )
            </>
          );
        }
        return null;
      };

      return (
        <>
          <Header as="h2">
            Recent Permission Errors {errorLink()}
            <Header.Subheader>
              This section shows Cloudtrail permission errors discovered for
              this resource in the last 24 hours.
            </Header.Subheader>
          </Header>
          <Table celled>
            {header}
            <Table.Body>{rows}</Table.Body>
          </Table>
        </>
      );
    }
    return (
      <>
        <Header as="h2">
          No Cloudtrail Errors
          <Header.Subheader>
            We didn&apos;t find recent Cloudtrail errors associated with this
            resource.
          </Header.Subheader>
        </Header>
      </>
    );
  };

  const s3Errors = () => {
    if (s3?.errors?.s3_errors?.length > 0) {
      const header = (
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>Error Call</Table.HeaderCell>
            {is_s3_resource ? (
              <Table.HeaderCell>Role ARN</Table.HeaderCell>
            ) : null}
            <Table.HeaderCell>Count</Table.HeaderCell>
            <Table.HeaderCell>Bucket Name</Table.HeaderCell>
            <Table.HeaderCell>Bucket Prefix</Table.HeaderCell>
            <Table.HeaderCell>Error Status</Table.HeaderCell>
            <Table.HeaderCell>Error Code</Table.HeaderCell>
          </Table.Row>
        </Table.Header>
      );

      const rows = [];
      s3.errors.s3_errors.forEach((error) => {
        rows.push(
          <Table.Row negative>
            <Table.Cell>{error.error_call}</Table.Cell>
            {is_s3_resource ? <Table.Cell>{error.role_arn}</Table.Cell> : null}
            <Table.Cell>{error.count}</Table.Cell>
            <Table.Cell>{error.bucket_name}</Table.Cell>
            <Table.Cell>{error.request_prefix}</Table.Cell>
            <Table.Cell>{error.status_text}</Table.Cell>
            <Table.Cell>{error.status_code}</Table.Cell>
          </Table.Row>
        );
      });

      const errorLink = () => {
        return s3?.error_url ? (
          <>
            (
            <a href={s3.error_url} rel="noopener noreferrer" target="_blank">
              Click here to see logs
            </a>
            )
          </>
        ) : null;
      };

      return (
        <>
          <Header as="h2">
            Recent S3 Errors {errorLink()}
            <Header.Subheader>
              This section shows the top S3 permission errors discovered for
              this resource in the last 24 hours.
            </Header.Subheader>
          </Header>
          <Table celled>
            {header}
            <Table.Body>{rows}</Table.Body>
          </Table>
        </>
      );
    }
    return (
      <>
        <Header as="h2">
          No errors
          <Header.Subheader>
            We didn&apos;t find any recent errors associated with this resource.
          </Header.Subheader>
        </Header>
      </>
    );
  };

  return (
    <>
      {cloudtrail && cloudTrailErrors()}
      {s3 && s3Errors()}
    </>
  );
};

export default Issues;
