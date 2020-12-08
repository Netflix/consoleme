import React from "react";
import { Header, Icon, List, Segment } from "semantic-ui-react";

function RoleDetails(props) {
  const role = props.role;
  if (!role) {
    return (
      <Segment placeholder>
        <Header icon>
          <Icon name="braille" />
          No Role is selected for display.
        </Header>
      </Segment>
    );
  }

  return (
    <List divided relaxed="very">
      <List.Item>
        <List.Icon name="key" />
        <List.Content>
          <List.Header>Account</List.Header>
          <List.Description>
            {`${role.account_name} (${role.account_id})`}
          </List.Description>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Icon name="code" />
        <List.Content>
          <List.Header>Application</List.Header>
          <List.List>
            {role.apps.app_details.map((app) => (
              <List.Item>
                <List.Icon name="file code" />
                <List.Content>
                  <List.Header>
                    <a
                      target="_blank"
                      href={app.app_url}
                      rel="noopener noreferrer"
                    >
                      {app.name}
                    </a>
                  </List.Header>
                  <List.Description>{app.owner}</List.Description>
                </List.Content>
              </List.Item>
            ))}
          </List.List>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Icon name="edit" />
        <List.Content>
          <List.Header>Role</List.Header>
          <List.List>
            <List.Item>
              <List.Icon name="file" />
              <List.Content>
                <List.Header>NAME</List.Header>
                <List.Description>{role.name}</List.Description>
              </List.Content>
            </List.Item>
            <List.Item>
              <List.Icon name="file alternate" />
              <List.Content>
                <List.Header>ARN</List.Header>
                <List.Description>
                  <a
                    target="_blank"
                    rel="noopener noreferrer"
                    href={`/policies/edit/${role.account_id}/iamrole/${role.name}`}
                  >
                    {role.arn}
                  </a>
                </List.Description>
              </List.Content>
            </List.Item>
            <List.Item>
              <List.Icon name="tags" />
              <List.Content>
                <List.Header>TAGS</List.Header>
                <List.List>
                  {role.tags.map((tag) => (
                    <List.Item>
                      <List.Icon name="tag" />
                      <List.Content>
                        <List.Header>{tag.Key}</List.Header>
                        <List.Description>{tag.Value}</List.Description>
                      </List.Content>
                    </List.Item>
                  ))}
                </List.List>
              </List.Content>
            </List.Item>
            <List.Item>
              <List.Icon name="clone" />
              <List.Content>
                <List.Header>Template</List.Header>
                <List.Description>
                  {role.templated
                    ? "This is role is templated"
                    : "There is no template for this role"}
                </List.Description>
              </List.Content>
            </List.Item>
          </List.List>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Icon name="history" />
        <List.Content>
          <List.Header>Activity</List.Header>
          <List.List>
            <List.Item>
              <List.Icon name="cloud" />
              <List.Content>
                <List.Header>Cloud Trails</List.Header>
                <List.Description>
                  There are{" "}
                  <a
                    href={role.cloudtrail_details.error_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {role.cloudtrail_details.errors.cloudtrail_errors.length}
                  </a>{" "}
                  errors.
                </List.Description>
              </List.Content>
            </List.Item>
            <List.Item>
              <List.Icon name="bitbucket" />
              <List.Content>
                <List.Header>S3 Access Logs</List.Header>
                <List.Description>
                  There are{" "}
                  <a
                    href={role.s3_details.error_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {role.s3_details.errors.s3_errors.length}
                  </a>{" "}
                  errors.
                </List.Description>
              </List.Content>
            </List.Item>
          </List.List>
        </List.Content>
      </List.Item>
    </List>
  );
}

export default RoleDetails;
