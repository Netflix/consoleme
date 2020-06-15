import _ from 'lodash';
import React, {Component} from 'react';
import {generateBasePolicy} from '../helpers/utils';
import {
    Button,
    Form,
    Header,
    Message,
} from 'semantic-ui-react';


class SelfServiceComponentRoute53 extends Component {
    static TYPE = 'route53';
    static NAME = 'Route53';
    static ACTIONS = [
        {
            key: 'list',
            text: "List Records",
            value: "list",
            actions: [
                "route53:listresourcerecordsets",
            ],
        },
        {
            key: 'change',
            text: "Change Records",
            value: "change",
            actions: [
                "route53:changeresourcerecordsets",
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
            const result = _.find(SelfServiceComponentRoute53.ACTIONS, {"key": action});
            policy["Action"].push(...result.actions);
        });

        const permission = {
            service: SelfServiceComponentRoute53.TYPE,
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
                    Route53
                    <Header.Subheader>
                        Please Select Route53 Permissions from the below dropdown.
                    </Header.Subheader>
                </Header>
                <Form.Field>
                    <label>Select Permissions</label>
                    <Form.Dropdown
                        placeholder=""
                        multiple
                        selection
                        options={SelfServiceComponentRoute53.ACTIONS}
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

export default SelfServiceComponentRoute53;
