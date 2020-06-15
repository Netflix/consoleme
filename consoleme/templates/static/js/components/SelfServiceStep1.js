import _ from 'lodash';
import React, {Component} from 'react';
import {
    Dimmer,
    Form,
    Grid,
    Header,
    Loader,
    Search,
    Segment,
} from 'semantic-ui-react';
import RoleDetails from "./RoleDetails";


class SelfServiceStep1 extends Component {
    state = {
        isLoading: false,
        isRoleLoading: false,
        results: [],
        value: '',
    };

    handleSearchChange(event, {value}) {
        this.setState({
            isLoading: true,
            value,
        });

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
                                memo[name] = {name, results};
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
        this.setState({
            value: result.title,
            isRoleLoading: true,
        });
        const roleName = result.title.split("/")[1]
        const accountId = result.title.split(":")[4]
        fetch(`/api/v2/roles/${accountId}/${roleName}`).then((resp) => {
            resp.text().then((resp) => {
                const role = JSON.parse(resp);
                this.props.handleRoleUpdate(role);
                this.setState({
                    isLoading: false,
                    isRoleLoading: false,
                    value: role.arn,
                });
            });
        });
    }

    render() {
        const role = this.props.role;
        const {isLoading, isRoleLoading, results, value} = this.state;

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
                                For Help, please visit <a
                                href={"https://go/selfserviceiamtldr"}>go/selfserviceiamtldr</a>
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
                                        value={value}
                                    />
                                </Form.Field>
                            </Form>
                        </Grid.Column>
                        <Grid.Column>
                            <Header>
                                Role Information
                            </Header>
                            {
                                isRoleLoading
                                    ? <Loader active={isRoleLoading} />
                                    : <RoleDetails role={role} />
                            }
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            </Segment>
        );
    }
}

export default SelfServiceStep1;
