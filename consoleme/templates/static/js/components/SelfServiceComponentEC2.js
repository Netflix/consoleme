import React, {Component} from 'react';
import {
    Form,
    Header,
} from 'semantic-ui-react';

const actionOptions = [
    { key: 'volmount', text: "Volume Mount", value: "volmount" },
];


class SelfServiceComponentEC2 extends Component {
    static TYPE = 'ec2';
    static NAME = 'EC2';

    state = {
    };

    componentDidMount() {
    }

    handleActionChange(e, {value}) {
        const {permission} = this.props;

        this.props.updatePermission({
            type: SelfServiceComponentEC2.TYPE,
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
                        Please Select EC2 Permissions from the below dropdown.
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

export default SelfServiceComponentEC2;
