import _ from 'lodash';
import React, {Component} from 'react';
import {
    Form,
    Grid,
    Header,
    Loader,
    Message,
    Search,
    Segment,
} from 'semantic-ui-react';
import RoleDetails from "./RoleDetails";
import "./SelfService.css";

const ARN_REGEX = /^arn:aws:iam::(?<accountId>\d{12}):role\/(?<roleName>.+)$/;

class SelfServiceStep1 extends Component {
    state = {
        isLoading: false,
        isRoleLoading: false,
        messages: [],
        results: [],
        value: '',
    };

    handleSearchChange(event, {value}) {
        this.setState({
            isLoading: true,
            value,
        }, () => {
            const match = ARN_REGEX.exec(value);
            if (match) {
                let {groups: {accountId, roleName}} = match;
                roleName = roleName.split('/').splice(-1, 1)[0];
                fetch(`/api/v2/roles/${accountId}/${roleName}`).then((resp) => {
                    resp.text().then((resp) => {
                        // if the given role doesn't exist.
                        const response = JSON.parse(resp);
                        if (response.status === 404) {
                            this.props.handleRoleUpdate(null);
                            this.setState({
                                isLoading: false,
                                messages: [response.message],
                            });
                        } else {
                            const role = response;
                            this.props.handleRoleUpdate(role);
                            this.setState({
                                isLoading: false,
                                value: role.arn,
                                messages: [],
                            });
                        }
                    });
                });
            } else {
                // If the given ARN is not a valid one.
                this.setState({
                    isLoading: false,
                }, () => {
                    this.props.handleRoleUpdate(null);
                });
            }
        });

        setTimeout(() => {
            const {value} = this.state;
            if (value.length < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        messages: [],
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
        }, () => {
            const match = ARN_REGEX.exec(result.title);
            if (match) {
                let {groups: {accountId, roleName}} = match;
                roleName = roleName.split('/').splice(-1, 1)[0];
                fetch(`/api/v2/roles/${accountId}/${roleName}`).then((resp) => {
                    resp.text().then((resp) => {
                        const role = JSON.parse(resp);
                        this.props.handleRoleUpdate(role);
                        this.setState({
                            isLoading: false,
                            isRoleLoading: false,
                            messages: [],
                            value: role.arn,
                        });
                    });
                });
            }
        });
    }

    render() {
        const role = this.props.role;
        const {isLoading, isRoleLoading, messages, results, value} = this.state;
        const messagesToShow = (messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        We found some problems for this request.
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
            <Segment>
                {messagesToShow}
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
                                href={"http://go/selfserviceiamtldr"} target={"_blank"}>go/selfserviceiamtldr</a>
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
                                Selected Role Information
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
