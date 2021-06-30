import React from "react";
import { Grid, Header, Icon, Label, Segment, Table } from "semantic-ui-react";
import { zip } from "lodash";

function RoleDetails(props) {
  const role = props.role;

  if (!role) {
    return (
      <Grid style={{ height: "100%" }}>
        <Grid.Row>
          <Grid.Column textAlign="center" verticalAlign="middle">
            <div>
              <Header as="h3">
                Search a principal to modify to view details about it.
              </Header>
            </div>
          </Grid.Column>
        </Grid.Row>
      </Grid>
    );
  }

  // TODO: swap out `template_language` for `templated` Boolean
  // once the API has changed.
  if (role.template_language === "honeybee") {
    // Zip the include and exclude accounts for display in a Table format.
    const includeExcludeAccounts = zip(
      role.include_accounts,
      role.exclude_accounts
    );
    return (
      <>
        <Segment basic style={{ borderTop: "1px solid rgba(34,36,38,.15)" }}>
          <Label
            color="blue"
            attached="top left"
            style={{
              borderTopLeftRadius: "0",
              paddingLeft: "40px",
              paddingRight: "40px",
            }}
          >
            Templated Role
          </Label>
        </Segment>
        <div style={{ display: "flex" }}>
          <Icon
            name="users"
            style={{ flexShrink: 0, width: "40px" }}
            size="large"
          />
          <div>
            <Header as="h3">{role.name}</Header>
            <Grid relaxed="very">
              <Grid.Row>
                <Grid.Column width={16}>
                  <Header as="h5">
                    PATH
                    <Header.Subheader>
                      <a
                        href={role.web_path}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {role.file_path}
                      </a>
                    </Header.Subheader>
                  </Header>
                </Grid.Column>
              </Grid.Row>
              <Grid.Row>
                <Grid.Column width={8}>
                  <Header as="h5">
                    OWNER
                    <Header.Subheader>{role.owner}</Header.Subheader>
                  </Header>
                </Grid.Column>
                <Grid.Column width={8}>
                  <Header as="h5">
                    TEMPLATE LANGUAGE
                    <Header.Subheader>
                      {role.template_language}
                    </Header.Subheader>
                  </Header>
                </Grid.Column>
              </Grid.Row>
              <Grid.Row>
                <Grid.Column width={8}>
                  <Header as="h5" style={{ marginBottom: 0 }}>
                    NUMBER OF AFFECTED ACCOUNTS
                  </Header>
                  <Label circular style={{ marginTop: 3, marginBottom: 4 }}>
                    {role.number_of_accounts}
                  </Label>{" "}
                  Affected Accounts
                </Grid.Column>
                <Grid.Column width={8}>
                  <Header as="h5">
                    RESOURCE TYPE
                    <Header.Subheader>{role.resource_type}</Header.Subheader>
                  </Header>
                </Grid.Column>
              </Grid.Row>
              {includeExcludeAccounts.length > 0 ? (
                <Grid.Row>
                  <Grid.Column width={16}>
                    <Header as="h5" style={{ marginBottom: 0 }}>
                      ACCOUNTS
                    </Header>
                    <Table
                      basic="very"
                      compact="very"
                      striped
                      size="small"
                      style={{ marginTop: 0 }}
                    >
                      <Table.Header>
                        <Table.Row>
                          <Table.HeaderCell
                            width={8}
                            style={{ paddingLeft: "1.5em", paddingBottom: 0 }}
                          >
                            INCLUDED
                          </Table.HeaderCell>
                          <Table.HeaderCell
                            width={8}
                            style={{ paddingLeft: "1.5em", paddingBottom: 0 }}
                          >
                            EXCLUDED
                          </Table.HeaderCell>
                        </Table.Row>
                      </Table.Header>
                      <Table.Body>
                        {includeExcludeAccounts.map((accts, index) => {
                          return (
                            <Table.Row key={`accts${index}`}>
                              <Table.Cell style={{ paddingLeft: "1.5em" }}>
                                {accts[0] ? accts[0] : ""}
                              </Table.Cell>
                              <Table.Cell style={{ paddingLeft: "1.5em" }}>
                                {accts[1] ? accts[1] : ""}
                              </Table.Cell>
                            </Table.Row>
                          );
                        })}
                      </Table.Body>
                    </Table>
                  </Grid.Column>
                </Grid.Row>
              ) : null}
            </Grid>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div style={{ display: "flex" }}>
        <Icon
          name="user"
          style={{ flexShrink: 0, width: "40px" }}
          size="large"
        />
        <div>
          <Header as="h3">{role.name}</Header>
          <Grid relaxed="very">
            <Grid.Row>
              <Grid.Column width={16}>
                <Header as="h5">
                  ARN
                  <Header.Subheader>
                    <a
                      target="_blank"
                      rel="noopener noreferrer"
                      href={`/policies/edit/${role.account_id}/iamrole/${role.name}`}
                    >
                      {role.arn}
                    </a>
                  </Header.Subheader>
                </Header>
              </Grid.Column>
            </Grid.Row>
            <Grid.Row>
              <Grid.Column width={8}>
                <Header as="h5">
                  ACCOUNT
                  <Header.Subheader>
                    <strong>{role.account_name}</strong>
                    <br />
                    {role.account_id}
                  </Header.Subheader>
                </Header>
              </Grid.Column>
              <Grid.Column width={8}>
                <Header as="h5">
                  APPLICATION
                  <Header.Subheader>
                    {role.apps.app_details.map((app) => (
                      <div key={app.name}>
                        <a
                          target="_blank"
                          href={app.app_url}
                          rel="noopener noreferrer"
                        >
                          {app.name}
                        </a>
                        {app.owner}
                      </div>
                    ))}
                  </Header.Subheader>
                </Header>
              </Grid.Column>
            </Grid.Row>
            <Grid.Row>
              <Grid.Column width={8}>
                <Header as="h5" style={{ marginBottom: 0 }}>
                  ACTIVITY
                </Header>
                <div style={{ marginTop: 3, marginBottom: 4 }}>
                  <Label circular>
                    {role.cloudtrail_details.errors.cloudtrail_errors.length}
                  </Label>{" "}
                  Cloud Trails Errors
                </div>
                <div>
                  <Label circular>
                    {role.s3_details.errors.s3_errors.length}
                  </Label>{" "}
                  S3 Access Log Errors
                </div>
              </Grid.Column>
              <Grid.Column width={8}>
                <Header as="h5" style={{ marginBottom: 0 }}>
                  RESOURCE TYPE
                </Header>
                <div>{role.resource_type}</div>
              </Grid.Column>
            </Grid.Row>
            {role.tags.length > 0 ? (
              <Grid.Row>
                <Grid.Column width={16}>
                  <Header as="h5" style={{ marginBottom: 0 }}>
                    TAGS
                  </Header>
                  <Table
                    basic="very"
                    compact="very"
                    striped
                    size="small"
                    style={{ marginTop: 0 }}
                  >
                    <Table.Header>
                      <Table.Row>
                        <Table.HeaderCell
                          width={8}
                          style={{ paddingLeft: "1.5em", paddingBottom: 0 }}
                        >
                          NAME
                        </Table.HeaderCell>
                        <Table.HeaderCell
                          width={8}
                          style={{ paddingLeft: "1.5em", paddingBottom: 0 }}
                        >
                          VALUE
                        </Table.HeaderCell>
                      </Table.Row>
                    </Table.Header>
                    <Table.Body>
                      {role.tags.map((tag) => {
                        return (
                          <Table.Row key={tag.Key}>
                            <Table.Cell style={{ paddingLeft: "1.5em" }}>
                              {tag.Key}
                            </Table.Cell>
                            <Table.Cell style={{ paddingLeft: "1.5em" }}>
                              {tag.Value}
                            </Table.Cell>
                          </Table.Row>
                        );
                      })}
                    </Table.Body>
                  </Table>
                </Grid.Column>
              </Grid.Row>
            ) : null}
          </Grid>
        </div>
      </div>
    </>
  );
}

export default RoleDetails;
