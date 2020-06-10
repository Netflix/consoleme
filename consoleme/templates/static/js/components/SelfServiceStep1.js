import _ from 'lodash';
import React, {Component} from 'react';
import {
    Form,
    Grid,
    Header,
    Search,
    Segment,
} from 'semantic-ui-react';


class SelfServiceStep1 extends Component {
    state = {
        isLoading: false,
        results: [],
        value: '',
        roleInfo: '',
    };

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
        // TODO(iam), once we select a role, fetch the role info and update the Role Info section.
        const roleName = result.title.split("/")[1]
        const accountId = result.title.split(":")[4]

        // const res = detch (`/roles/${accountId}/${roleName}`);
        fetch(`/api/v2/roles/${accountId}/${roleName}`).then((resp) => {
            resp.text().then((source) => {
                this.setState({
                    isLoading: false,
                    roleInfo: source,
                });
            });
        });

        role.roleArn = result.title;
        this.props.handleRoleUpdate(role);
        this.setState({
            value: role.roleArn,
        });
    }

    render() {
        const {roleArn} = this.props.role;
        const {isLoading, results, roleInfo} = this.state;

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
                                <Form.Field required>
                                    <label>Search Your Application Roles</label>
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
                                <Form.Checkbox label='Show all entities' checked />
                            </Form>
                        </Grid.Column>
                        <Grid.Column>
                            <Header>
                                Role Information
                            </Header>
                            <Segment placeholder>
                                {roleInfo}
                            </Segment>
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            </Segment>
        );
    }
}

export default SelfServiceStep1;
