import _ from 'lodash';
import React, {Component} from 'react';
import {generateBasePolicy} from '../helpers/utils';
import {
    Button,
    Form,
    Header,
    Message,
} from 'semantic-ui-react';


class SelfServiceComponentRDS extends Component {
    static TYPE = 'rds';
    static NAME = 'RDS';
    static ACTIONS = [
        {
            key: 'passrole',
            text: "Passrole to rds-monitoring-role",
            value: "passrole",
            actions: [
                "iam:PassRole",
            ]
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
        const {role} = this.props;

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

        const resource = `arn:aws:iam::${role.account_id}:role/rds-monitoring-role`
        policy["Resource"] = [resource];

        actions.forEach(action => {
            const result = _.find(SelfServiceComponentRDS.ACTIONS, {"key": action});
            policy["Action"].push(...result.actions);
        });

        const permission = {
            service: SelfServiceComponentRDS.TYPE,
            actions,
            policy,
            value: resource,
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
                    RDS
                    <Header.Subheader>
                        Please Select RDS Permissions from the below dropdown.
                    </Header.Subheader>
                </Header>
                <Form.Field>
                    <label>Select Permissions</label>
                    <Form.Dropdown
                        placeholder=""
                        multiple
                        selection
                        options={SelfServiceComponentRDS.ACTIONS}
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

export default SelfServiceComponentRDS;
