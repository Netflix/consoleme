import _ from 'lodash';
import React, {Component} from 'react';
import {generateBasePolicy} from '../helpers/utils';
import {
    Button,
    Form,
    Header,
    Message,
} from 'semantic-ui-react';


class SelfServiceComponentEC2 extends Component {
    static TYPE = 'ec2';
    static NAME = 'EC2';
    static ACTIONS = [
        {
            key: 'volmount',
            text: "Volume Mount",
            value: "volmount",
            actions: [
                "ec2:attachvolume",
                "ec2:createvolume",
                "ec2:describelicenses",
                "ec2:describevolumes",
                "ec2:detachvolume",
                "ec2:reportinstancestatus",
                "ec2:resetsnapshotattribute",
            ],
        },
    ];

    state = {
        actions: [],
        messages: [],
    };

    handleActionChange(e, {value}) {
        this.setState({
            actions: value,
        });
    }

    handleSubmit() {
        const {actions} = this.state;
        const messages = [];
        if (!actions.length) {
            messages.push("No actions is selected.")
        }
        if (messages.length > 0) {
            return this.setState({
                messages,
            });
        }
        const policy = generateBasePolicy();
        policy["Resource"] = ["*"];
        actions.forEach(action => {
            const result = _.find(SelfServiceComponentEC2.ACTIONS, {"key": action});
            policy["Action"].push(...result.actions);
        });
        const permission = {
            service: SelfServiceComponentEC2.TYPE,
            actions,
            policy,
            value: "*",
        };
        return this.setState({
            actions: [],
            messages: [],
        }, () => {
            this.props.updatePermission(permission);
        });
    }

    render() {
        const {actions, messages} = this.state;
        const messagesToShow = (messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        There are some parameters missing.
                    </Message.Header>
                    <Message.List>
                        {
                            messages.map(message => {
                                return <Message.Item>{message}</Message.Item>;
                            })
                        }
                    </Message.List>
                </Message>
            )
            : null;

        return (
            <Form>
                <Header as="h3">
                    EC2
                    <Header.Subheader>
                        Please Select EC2 Permissions from the below dropdown.
                    </Header.Subheader>
                </Header>
                <Form.Field required>
                    <label>Select Permissions</label>
                    <Form.Dropdown
                        placeholder=""
                        multiple
                        selection
                        options={SelfServiceComponentEC2.ACTIONS}
                        value={actions}
                        onChange={this.handleActionChange.bind(this)}
                    />
                </Form.Field>
                {messagesToShow}
                <Button
                    fluid
                    onClick={this.handleSubmit.bind(this)}
                    primary
                    type='submit'
                >
                    Add Permission
                </Button>
            </Form>
        );
    }
}

export default SelfServiceComponentEC2;
