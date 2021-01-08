import _ from "lodash";
import React, { useState } from "react";
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

const SelfServiceStep2 = (props) => {
  const initialState = {
    service: DEFAULT_AWS_SERVICE,
  };

  const [state, setState] = useState(initialState);

  const handleServiceTypeChange = (e, { value }) => {
    setState({
      ...state,
      service: value,
    });
  };

  const handlePermissionAdd = (permission) => {
    setState({
      ...state,
      service: null,
    });
    const cb = () => {
      const { permissions } = props;
      permissions.push(permission);
      props.handlePermissionsUpdate(permissions);
    };
    cb();
  };

  const handlePermissionRemove = (target) => {
    const { permissions } = props;
    _.remove(permissions, (permission) => _.isEqual(target, permission));
    props.handlePermissionsUpdate(permissions);
  };

  const getPermissionItems = () => {
    const { config, services } = props;

    return props.permissions.map((permission, idx) => {
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
                onClick={() => handlePermissionRemove(this, permission)}
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
  };

  const { config, role, services } = props;
  const { service } = state;

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
                onChange={() => handleServiceTypeChange()}
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
                updatePermission={() => handlePermissionAdd()}
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
            <Item.Group divided>{() => getPermissionItems()}</Item.Group>
            <Divider />
          </Grid.Column>
        </Grid.Row>
      </Grid>
    </Segment>
  );
};

export default SelfServiceStep2;
