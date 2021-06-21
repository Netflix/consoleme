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
  TextArea, Message,
} from "semantic-ui-react";
import SelfServiceComponent from "./SelfServiceComponent";
import SelfServiceModal from './SelfServiceModal.js';

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = "s3";

class SelfServiceStep2 extends Component {
  constructor(props) {
    super(props);
    this.state = {
      service: DEFAULT_AWS_SERVICE,
      activeIndex: 0,
      custom_statement: "",
      isError: false,
      isLoading: false,
      isSuccess: false,
      justification: "",
      messages: [],
      requestId: null,
      statement: "",
      admin_bypass_approval_enabled: this.props.admin_bypass_approval_enabled,
      export_to_terraform_enabled: this.props.export_to_terraform_enabled,
      admin_auto_approve: false,
      policy_name: "",
    };

    this.inlinePolicyEditorRef = React.createRef();
    this.terraformPolicyExporterRef = React.createRef();
    this.onChange = this.onChange.bind(this);
    // this.handleJustificationChange = this.handleJustificationChange.bind(this);
    // this.handleSubmit = this.handleSubmit.bind(this);
    // this.handleAdminSubmit = this.handleAdminSubmit.bind(this);
  }

  /*async componentDidMount() {
    const { role, permissions } = this.props;
    const payload = {
      changes: [],
    };
    payload.changes = permissions.map((permission) => {
      const change = {
        principal: {
          principal_arn: role.arn,
          principal_type: "AwsResource",
        },
        generator_type: permission.service,
        action_groups: permission.actions,
        condition: permission.condition,
        effect: "Allow",
        ...permission,
      };
      delete change.service;
      delete change.actions;
      return change;
    });

    const response = await this.props.sendRequestCommon(
      payload,
      "/api/v2/generate_changes"
    );
    if (response.status != null && response.status === 400) {
      return this.setState({
        isError: true,
        messages: [response.message],
      });
    }

    if ("changes" in response && response.changes.length > 0) {
      const policy_name = response.changes[0].policy_name;
      const statement = JSON.stringify(
        response.changes[0].policy.policy_document,
        null,
        4
      );
      return this.setState({
        custom_statement: statement,
        isError: false,
        messages: [],
        policy_name,
        statement,
      });
    }
    return this.setState({
      isError: true,
      messages: ["Unknown Exception raised. Please reach out for support"],
    });
  } */








  onChange(newValue, e) {
    this.setState({
      custom_statement: newValue,
    });
  }

  handleServiceTypeChange(e, { value }) {
    this.setState({
      service: value,
    });
  }

  handleExtraActionsAdd(extraAction) {
    const {extraActions} = this.props;
    extraActions.push.apply(extraActions, extraAction);
    this.props.handleExtraActionsUpdate(extraActions);
  }

  handleIncludeAccountsAdd(includeAccount) {
    const {includeAccounts} = this.props;
    includeAccounts.push.apply(includeAccounts, includeAccount);
    this.props.handleIncludeAccountsUpdate(includeAccounts);
  }

  handleExcludeAccountsAdd(excludeAccount) {
    const {excludeAccounts} = this.props;
    excludeAccounts.push.apply(excludeAccounts, excludeAccount);
    this.props.handleExcludeAccountsUpdate(excludeAccounts);
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
    const {
      admin_bypass_approval_enabled,
      custom_statement,
      export_to_terraform_enabled,
      isError,
      isLoading,
      isSuccess,
      justification,
      messages,
      requestId,
      statement,
    } = this.state;

    const active = custom_statement !== statement;
    const messagesToShow =
      messages.length > 0 ? (
        <Message negative>
          <Message.Header>
            We found some problems for this request.
          </Message.Header>
          <Message.List>
            {messages.map((message) => (
              <Message.Item>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      ) : null;

    const headerMessage =
       role.arn ? (
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
       ) :
          <Header>
            Modify Policy
            <Header.Subheader>
              You can choose the resource(s) you wish to modify and the actions you wish to add.
              Advanced options include specified actions, include and exclude accounts.
              <a
                 href={`/policies/edit/${role.account_id}/iamrole/${role.owner}`}
                 target="_blank"
                 rel="noopener noreferrer"
              >
                {role.resource}
              </a>
              .&nbsp; You can also select multiple permissions.
            </Header.Subheader>
          </Header>;



    return (
      <Segment>
        <Grid columns={2} divided>
          <Grid.Row>
            <Grid.Column>
              <Header>
                {headerMessage}
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
                  updateExtraActions={this.handleExtraActionsAdd.bind(this)}
                  updateIncludeAccounts={this.handleIncludeAccountsAdd.bind(this)}
                  updateExcludeAccounts={this.handleExcludeAccountsAdd.bind(this)}
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
              <Header>
                You must add at least one resource to continue
                or choose <SelfServiceModal
                            {...this.props}
                          /> to override permissions.
              </Header>
              {messagesToShow}
            </Grid.Column>
          </Grid.Row>
        </Grid>
      </Segment>
    );
  }
}

export default SelfServiceStep2;
