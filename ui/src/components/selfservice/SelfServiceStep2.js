import _ from "lodash";
import React, { Component } from "react";
import {
  Button,
  Divider,
  Form,
  Grid,
  Icon,
  Item,
  Label,
  List,
  Header,
  Segment,
} from "semantic-ui-react";
import SelfServiceComponent from "./SelfServiceComponent";

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = "s3";

class SelfServiceStep2 extends Component {
  constructor(props) {
    super(props);
    this.state = {
      service: DEFAULT_AWS_SERVICE,
    };
  }

  handleServiceTypeChange(e, { value }) {
    this.setState({
      service: value,
    });
  }

  handlePermissionAdd(permission) {
    this.setState(
      {
        service: null,
      },
      () => {
        const { permissions } = this.props;
        permissions.push(permission);
        this.props.handlePermissionsUpdate(permissions);
      }
    );
  }

  handlePermissionRemove(target) {
    const { permissions } = this.props;
    _.remove(permissions, (permission) => _.isEqual(target, permission));
    this.props.handlePermissionsUpdate(permissions);
  }

  getPermissionItems() {
    const { config, services } = this.props;

    return this.props.permissions.map((permission, idx) => {
      const found = _.find(services, { key: permission.service });
      const serviceName = found.text;
      const { inputs } = config.permissions_map[found.key];
      return (
        <Item key={idx}>
          <Item.Content>
            <Item.Header>{serviceName}</Item.Header>
            <Item.Meta>
              <List relaxed>
                {Object.keys(permission).map((key) => {
                  if (
                    key === "actions" ||
                    key === "service" ||
                    key === "condition"
                  ) {
                    return null;
                  }
                  const inputConfig = _.find(inputs, { name: key });
                  return (
                    <List.Item>
                      <List.Header>{inputConfig.text}</List.Header>
                      {permission[key]}
                    </List.Item>
                  );
                })}
              </List>
            </Item.Meta>
            <Item.Extra>
              <Button
                size="tiny"
                color="red"
                floated="right"
                onClick={this.handlePermissionRemove.bind(this, permission)}
              >
                Remove
                <Icon name="right close" />
              </Button>
              {permission.actions != null
                ? permission.actions.map((action) => {
                    const actionDetail = _.find(found.actions, {
                      name: action,
                    });
                    return (
                      <Label as="a" color="olive">
                        <Icon name="caret right" />
                        {actionDetail.text}
                      </Label>
                    );
                  })
                : null}
            </Item.Extra>
          </Item.Content>
        </Item>
      );
    });
  }

  render() {
    const { config, role, services } = this.props;
    const { service } = this.state;
    return (
      <Segment>
        <Grid columns={2} divided>
          <Grid.Row>
            <Grid.Column>
              <Header>
                Add Permission
                <Header.Subheader>
                  Please add permissions to your role&nbsp;
                  <a
                    href={`/policies/edit/${role.account_id}/iamrole/${role.name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {role.arn}
                  </a>
                  .&nbsp; You can also select multiple permissions.
                </Header.Subheader>
              </Header>
              <Form>
                <Form.Select
                  value={service}
                  label="Select Desired Permissions"
                  onChange={this.handleServiceTypeChange.bind(this)}
                  options={services}
                  placeholder="Choose One"
                  required
                />
              </Form>
              <Divider />
              {service != null ? (
                <SelfServiceComponent
                  key={service}
                  config={config}
                  role={role}
                  service={service}
                  updatePermission={this.handlePermissionAdd.bind(this)}
                  {...this.props}
                />
              ) : null}
            </Grid.Column>
            <Grid.Column>
              <Header>
                Your Permissions
                <Header.Subheader>
                  The list of permission you have added in this request.
                </Header.Subheader>
              </Header>
              <Item.Group divided>{this.getPermissionItems()}</Item.Group>
              <Divider />
            </Grid.Column>
          </Grid.Row>
        </Grid>
      </Segment>
    );
  }
}

export default SelfServiceStep2;
