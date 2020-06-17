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
import SelfServiceComponent from "./SelfServiceComponent";
import {getServiceTypes} from '../helpers/utils';

// TODO, move this to config file.
const DEFAULT_AWS_SERVICE = 's3';

// List of available self service items.
const serviceTypeOptions = getServiceTypes();

class SelfServiceStep2 extends Component {
    state = {
        service: DEFAULT_AWS_SERVICE,
    };

    handleServiceTypeChange(e, {value}) {
        this.setState({
            service: value,
        });
    }

    handlePermissionAdd(permission) {
        this.setState({
            service: DEFAULT_AWS_SERVICE,
        }, () => {
            const {permissions} = this.props;
            permissions.push(permission);
            this.props.handlePermissionsUpdate(permissions);
        });
    }

    handlePermissionRemove(target) {
        const {permissions} = this.props;
        _.remove(permissions, (permission) => _.isEqual(target, permission));
        this.props.handlePermissionsUpdate(permissions);
    }

    getPermissionItems() {
        return this.props.permissions.map((permission, idx) => {
            const found = _.find(serviceTypeOptions, {"key": permission.service});
            const serviceName = found.text;
            return (
                <Item key={idx}>
                    <Item.Content>
                        <Item.Header>
                            {serviceName}
                        </Item.Header>
                        <Item.Meta>
                            {permission.value}
                        </Item.Meta>
                        <Item.Extra>
                            <Button
                                size="tiny"
                                color="red"
                                floated='right'
                                onClick={this.handlePermissionRemove.bind(this, permission)}
                            >
                                Remove
                                <Icon name='right close' />
                            </Button>
                            {
                                permission.actions.map(action => {
                                    const actionDetail = _.find(found.actions, {"key": action});
                                    return (
                                        <Label as="a" color="green">
                                            {actionDetail.text}
                                        </Label>
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
        const {role} = this.props;

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
                                    value={this.state.service}
                                    label="Select AWS Service"
                                    onChange={this.handleServiceTypeChange.bind(this)}
                                    options={serviceTypeOptions}
                                    placeholder='Choose One'
                                    required
                                />
                            </Form>
                            <Divider />
                            <SelfServiceComponent
                                role={role}
                                service={this.state.service}
                                updatePermission={this.handlePermissionAdd.bind(this)}
                            />
                        </Grid.Column>
                        <Grid.Column>
                            <Header>
                                Your Permissions
                                <Header.Subheader>
                                    The list of permission you have added in this request.
                                </Header.Subheader>
                            </Header>
                            <Item.Group divided>
                                {this.getPermissionItems()}
                            </Item.Group>
                            <Divider />
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            </Segment>
        );
    }
}

export default SelfServiceStep2;
