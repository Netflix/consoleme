/* eslint-disable camelcase */
import React from "react";
import { Message, Table } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";

const ResourceDetail = () => {
  const { params = {}, resource = {} } = usePolicyContext();
  const { serviceType = "iamrole" } = params;
  const {
    account_id,
    account_name,
    arn,
    name,
    s3_details,
    templated,
    template_link,
    config_timeline_url,
    resource_details,
    last_used_time,
    description,
  } = resource;

  const created_time = resource.created_time || resource_details?.created_time;

  return (
    <>
      <Table celled striped definition>
        <Table.Body>
          <Table.Row>
            <Table.Cell width={4}>Account</Table.Cell>
            <Table.Cell>{`${account_name} (${account_id}`})</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Amazon Resource Name</Table.Cell>
            <Table.Cell>{arn}</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Resource type</Table.Cell>
            <Table.Cell>{serviceType}</Table.Cell>
          </Table.Row>
          {name ? (
            <Table.Row>
              <Table.Cell>Resource name</Table.Cell>
              <Table.Cell>{name}</Table.Cell>
            </Table.Row>
          ) : null}
          {description ? (
            <Table.Row>
              <Table.Cell>Description</Table.Cell>
              <Table.Cell>{description}</Table.Cell>
            </Table.Row>
          ) : null}
          {s3_details && s3_details.error_url ? (
            <Table.Row>
              <Table.Cell>S3 Access Log</Table.Cell>
              <Table.Cell>
                <a
                  href={(s3_details && s3_details.error_url) || ""}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  Link
                </a>
              </Table.Cell>
            </Table.Row>
          ) : null}
          {resource?.resource_details?.QueueUrl ? (
            <Table.Row>
              <Table.Cell>Queue Url</Table.Cell>
              <Table.Cell>{resource.resource_details.QueueUrl}</Table.Cell>
            </Table.Row>
          ) : null}
          {config_timeline_url ? (
            <Table.Row>
              <Table.Cell>Config Timeline</Table.Cell>
              <Table.Cell>
                <a
                  href={config_timeline_url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  Link
                </a>
              </Table.Cell>
            </Table.Row>
          ) : null}
          {created_time ? (
            <Table.Row>
              <Table.Cell>Created on</Table.Cell>
              <Table.Cell>{created_time}</Table.Cell>
            </Table.Row>
          ) : null}
          {last_used_time ? (
            <Table.Row>
              <Table.Cell>Last Used on</Table.Cell>
              <Table.Cell>{last_used_time}</Table.Cell>
            </Table.Row>
          ) : null}
          {resource_details?.updated_time ? (
            <Table.Row>
              <Table.Cell>Last Updated</Table.Cell>
              <Table.Cell>{resource_details.updated_time}</Table.Cell>
            </Table.Row>
          ) : null}
          <Table.Row>
            <Table.Cell>Templated</Table.Cell>
            <Table.Cell>
              <span>
                {`${templated ? "True" : "False"}`}
                {templated ? (
                  <>
                    {" "}
                    (
                    <a
                      href={template_link}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      Link
                    </a>
                    )
                  </>
                ) : null}
              </span>
            </Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
      {templated ? (
        <Message warning>
          <Message.Header>Templated Resource</Message.Header>
          <>
            This is a templated resource. Any changes you make here may be
            overwritten by the template.
          </>
          {template_link ? (
            <>
              {" "}
              You may view the template{" "}
              <a href={template_link} rel="noopener noreferrer" target="_blank">
                here
              </a>
              .
            </>
          ) : null}
        </Message>
      ) : null}
    </>
  );
};

export default ResourceDetail;
