import _ from 'lodash';
import React, {Component} from 'react';
import {
    Button,
    Divider,
    Form,
    Grid,
    Icon,
    Item,
    Label,
    Header,
    Segment,
} from 'semantic-ui-react';
import SelfServiceComponent from './SelfServiceComponent';

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = 's3';

// List of available self service items.
const resourceTypeOptions = Object.keys(SelfServiceComponent.components).map(service => {
    const component = SelfServiceComponent.components[service];
    return {
        key: component.TYPE,
        value: component.TYPE,
        text: component.NAME,
    };
});

const initializeState = {
    permission: {},
    resourceType: DEFAULT_AWS_SERVICE,
};


class SelfServiceStep1 extends Component {
    state = initializeState;

    handleResourceTypeChange(e, {value}) {
        this.setState({
            resourceType: value,
        });
    }

    handlePermissionAdd() {
        const {permission} = this.state;
        const {permissions} = this.props;

        // skip adding a permission if any of followings are empty.
        if (permission.value === '' || permission.actions.length < 1) {
            return;
        }

        permissions.push(permission);

        this.setState({
            permission: {},
            resourceType: DEFAULT_AWS_SERVICE,
        }, () => {
            this.props.handlePermissionsUpdate(permissions);
        });
    }

    handlePermissionRemove(p) {
        const {permissions} = this.props;
        _.remove(permissions, (e) => _.isEqual(p, e));

        this.props.handlePermissionsUpdate(permissions);
    }

    updatePermission(permission) {
        this.setState({
            permission,
        });
    }

    getPermissionItems() {
        return this.props.permissions.map((p, idx) => {
            return (
                <Item key={idx}>
                    <Item.Content>
                        <Item.Header>
                            {
                                // TODO, read resource title from its component.
                                resourceTypeOptions.filter(r => {
                                    return r.key === p.type;
                                })[0].text || ''
                            }
                        </Item.Header>
                        <Item.Meta>
                            {p.value}
                        </Item.Meta>
                        <Item.Extra>
                            <Button
                                size="tiny"
                                color="red"
                                floated='right'
                                onClick={this.handlePermissionRemove.bind(this, p)}
                            >
                                Remove
                                <Icon name='right close' />
                            </Button>
                            {
                                p.actions.map(a => {
                                    return (
                                        <Label>{a}</Label>
                                    );
                                })
                            }
                        </Item.Extra>
                    </Item.Content>
                </Item>
            )
        });
    }

    render() {
        const {permission, resourceType} = this.state;
        const permissionItems = this.getPermissionItems();

        return (
            <Segment>
                <Grid columns={2} divided>
                    <Grid.Row>
                        <Grid.Column>
                            <Header>
                                Add Permission
                                <Header.Subheader>
                                    Please add desired permissions. You can also select multiple permissions.
                                </Header.Subheader>
                            </Header>
                            <Form>
                                <Form.Select
                                    defaultValue={resourceType}
                                    label="Select AWS Service"
                                    onChange={this.handleResourceTypeChange.bind(this)}
                                    options={resourceTypeOptions}
                                    placeholder='Choose One'
                                    required
                                />
                            </Form>
                            <Divider />
                            <SelfServiceComponent
                                permission={permission}
                                service={resourceType}
                                updatePermission={this.updatePermission.bind(this)}
                            />
                            <Divider />
                            <Button
                                fluid
                                onClick={this.handlePermissionAdd.bind(this)}
                            >
                                Add Permission
                            </Button>
                        </Grid.Column>
                        <Grid.Column>
                            <Header>
                                Your Permissions
                                <Header.Subheader>
                                    The list of permission you have added in this request.
                                </Header.Subheader>
                            </Header>
                            <Item.Group divided>
                                {permissionItems}
                            </Item.Group>
                            <Divider />
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            </Segment>
        );
    }
}

export default SelfServiceStep1;
