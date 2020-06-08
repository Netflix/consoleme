import React, {Component} from 'react';
import {
    Form,
    Header,
} from 'semantic-ui-react';

const actionOptions = [
    { key: 'passrole', text: "Passrole to rds-monitoring-role", value: "passrole" },
];


class SelfServiceComponentRDS extends Component {
    static TYPE = 'rds';
    static NAME = 'RDS';

    state = {
    };

    componentDidMount() {
    }

    handleActionChange(e, {value}) {
        const {permission} = this.props;

        this.props.updatePermission({
            type: SelfServiceComponentRDS.TYPE,
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
                        Please Select RDS Permissions from the below dropdown.
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

export default SelfServiceComponentRDS;
