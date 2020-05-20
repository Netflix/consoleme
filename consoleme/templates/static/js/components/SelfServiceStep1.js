import _ from 'lodash';
import React, {Component} from 'react';
import {
    Form,
    Grid,
    Header,
    Search,
    Segment,
} from 'semantic-ui-react';


const sourceOptions = [
    { key: 'app', text: 'Applications', value: 'app' },
    { key: 'role', text: 'IAM Roles', value: 'role' },
];

class SelfServiceStep1 extends Component {
    state = {
        eligibleRoles: [],
        isLoading: false,
        results: [],
        value: '',
    };

    componentDidMount() {
        fetch("/api/v1/roles").then((resp) => {
            resp.json().then(({eligible_roles}) => {
                const eligibleRoles = eligible_roles.map((role) => {
                    return { key: role, text: role, value: role};
                });
                this.setState({
                    eligibleRoles,
                });
            });
        });
    }

    handleSearchChange(event, { value }) {
        this.setState({
            isLoading: true,
            value,
        });

        let role = Object.assign({}, this.props.role);
        role.roleArn = value;
        this.props.handleRoleUpdate(role);

        setTimeout(() => {
            const {value} = this.state;
            if (value.length < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        results: [],
                        value: '',
                    }
                );
            }

            const re = new RegExp(_.escapeRegExp(value), 'i');
            const isMatch = (result) => re.test(result.title);

            const TYPEAHEAD_API = '/policies/typeahead?resource=app&search=' + value;

            fetch(TYPEAHEAD_API).then((resp) => {
                resp.json().then((source) => {
                    const filteredResults = _.reduce(
                        source,
                        (memo, data, name) => {
                            const results = _.filter(data.results, isMatch);
                            if (results.length) {
                                memo[name] = { name, results };
                            }
                            return memo;
                        },
                        {},
                    );
                    this.setState({
                        isLoading: false,
                        results: filteredResults,
                    });
                });
            });
        }, 300);
    }

    handleResultSelect(e, {result}) {
        let role = Object.assign({}, this.props.role);
        role.roleArn = result.title;
        this.props.handleRoleUpdate(role);
        this.setState({
            value: role.roleArn,
        });
    }

    handleSelectRoleFromChange(e, {value}) {
        let role = Object.assign({}, this.props.role);
        role.roleFrom = value;
        this.props.handleRoleUpdate(role);
    }

    handleSelectRoleChange(e, {value}) {
        let role = Object.assign({}, this.props.role);
        role.roleArn = value;
        this.props.handleRoleUpdate(role);
    }

    render() {
        const {roleArn, roleFrom} = this.props.role;
        const {eligibleRoles, isLoading, results, value} = this.state;

        const sourceTypeSubInput = (roleFrom === 'app')
            ? (
                <Form.Field required>
                    <label>Search Roles</label>
                    <Search
                        category
                        loading={isLoading}
                        onResultSelect={this.handleResultSelect.bind(this)}
                        onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
                            leading: true,
                        })}
                        results={results}
                        value={roleArn}
                    />
                </Form.Field>
            )
            : (
                <Form.Select
                    required
                    label="Your Eligible Roles"
                    options={eligibleRoles}
                    search
                    placeholder="Choose Your Role"
                    value={roleArn}
                    onChange={this.handleSelectRoleChange.bind(this)}
                />
            );

        return (
            <Segment>
                <Grid columns={2} divided>
                    <Grid.Row>
                        <Grid.Column>
                            <Header>
                                Select a Role
                                <Header.Subheader>
                                    Please search for your role where you want to attach new permissions.
                                </Header.Subheader>
                            </Header>
                            <p>
                                For Help, please visit <a href={"https://go/selfserviceiamtldr"}>go/selfserviceiamtldr</a>
                            </p>
                            <Form widths="equal">
                                <Form.Select
                                    required
                                    label="Select Source Type"
                                    defaultValue={roleFrom}
                                    options={sourceOptions}
                                    placeholder='Select Source Type'
                                    onChange={this.handleSelectRoleFromChange.bind(this)}
                                />
                                {sourceTypeSubInput}
                                <Form.Checkbox label='Show all entities' checked />
                            </Form>
                        </Grid.Column>
                        <Grid.Column>
                            <Header>
                                Role Information
                            </Header>
                            <Segment placeholder />
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            </Segment>
        );
    }
}

export default SelfServiceStep1;
