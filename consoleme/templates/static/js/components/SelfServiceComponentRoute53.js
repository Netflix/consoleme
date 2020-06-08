import React, {Component} from 'react';
import {
    Form,
    Header,
} from 'semantic-ui-react';

const actionOptions = [
    { key: 'list', text: "List Records", value: "list" },
    { key: 'change', text: "Change Records", value: "change" },
];


class SelfServiceComponentRoute53 extends Component {
    static TYPE = 'route53';
    static NAME = 'Route53';

    state = {
    };

    componentDidMount() {
    }

    handleActionChange(e, {value}) {
        const {permission} = this.props;

        this.props.updatePermission({
            type: SelfServiceComponentRoute53.TYPE,
            actions: value,
            value: permission.value,
        });
    }

    render() {
        const {permission} = this.props;
        return (
            <Form>
                <Header as="h3">
                    EC2
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
                        options={actionOptions}
                        value={permission.actions || []}
                        onChange={this.handleActionChange.bind(this)}
                    />
                </Form.Field>
            </Form>
        );
    }
}

export default SelfServiceComponentRoute53;
