import _ from 'lodash'
import React, {Component} from 'react';
import {
    Button,
    Divider,
    Grid,
    Icon,
    Label,
    List,
    Header,
    Search,
    Segment,
} from 'semantic-ui-react';
import './Main.css';


const initialState = {
    isLoading: false,
    results: [],
    value: '',
    roles: [],
    selectedAccount: '',
    selectedRole: {
        account: "N/A",
        arn: "N/A",
        role: "N/A",
    },
    loading: true,
};

const resultRenderer = ({ account, role, arn }) => (
    <Label>
        {role}
        <Label.Detail>
            {account}
        </Label.Detail>
    </Label>
);

// resultRenderer.propTypes = {
//   title: PropTypes.string,
//   description: PropTypes.string,
// };

class Main extends Component {
    state = initialState;

    componentDidMount() {
        fetch(
            "/api/v1/roles", {
                mode: 'no-cors',
                credentials: 'include',
            }).then((res) => {
            res.json().then((resp) => {
                const roles = resp.reduce((roles, arn) => {
                    const match = arn.match(/^arn:aws:iam::(?<account>\d+):role\/(?<role>.+)$/);
                    const {role, account} = match.groups;
                    roles.push({key: arn, account, arn, role});
                    return roles;
                }, []);
                this.setState({
                    roles,
                    loading: false,
                });
            });
        });
    }

    handleResultSelect = (e, { result }) => {
        this.setState({
            selectedAccount: result.account,
            // value: '',
            // results: [],
            isLoading: false,
        });
    };

    handleSearchChange = (e, { value }) => {
        this.setState({ isLoading: true, value }, () => {
            if (this.state.value.length < 1) {
                this.setState({
                    isLoading: false,
                    value: '',
                    results: [],
                    selectedAccount: '',
                });
            }
            const re = new RegExp(_.escapeRegExp(this.state.value), 'i');
            const isMatch = (role) => re.test(role.arn);
            this.setState({
                isLoading: false,
                results: _.filter(this.state.roles, isMatch),
                 selectedAccount: '',
            });
        });
    };

    handleRoleDetailClick = (role, event) => {
        this.setState({
            selectedRole: role,
        })
    };

    handleSignInClick = (e) => {
        console.log(e);
    };

    render() {
        const { loading, isLoading, value, results, roles, selectedRole, selectedAccount } = this.state;

        let filtered = [];
        if (this.state.selectedAccount) {
            filtered = _.filter(roles, (role) => role.account == selectedAccount);
        } else {
            filtered = roles;
        }

        return (
            <Segment loading={loading} placeholder>
                <Grid columns={2} stackable textAlign='center'>
                    <Grid.Row verticalAlign='top'>
                        <Grid.Column>
                            <Header icon>
                                <Icon name='sign-in' />
                                Sign-In Account
                            </Header>
                            <Search
                                fluid
                                loading={isLoading}
                                onResultSelect={this.handleResultSelect}
                                onSearchChange={_.debounce(this.handleSearchChange, 500, {
                                    leading: true,
                                })}
                                results={results}
                                value={value}
                                placeholder="search account..."
                                resultRenderer={resultRenderer}
                            />
                            <Segment textAlign='left'>
                                <List selection celled verticalAlign='middle'>
                                    {
                                        filtered.map((role) => {
                                            return (
                                                <List.Item
                                                    active={role.role == selectedRole.role ? true : false}
                                                    key={role.arn}
                                                    onClick={this.handleRoleDetailClick.bind(this, role)}
                                                >
                                                    <Icon name="aws" color="orange" size="large" />
                                                    <List.Content>
                                                        <List.Header>{role.role}</List.Header>
                                                    </List.Content>
                                                    <Icon
                                                        onClick={this.handleRoleDetailClick.bind(this, role)}
                                                        name="file text"
                                                        size="large"
                                                    />
                                                    <Icon
                                                        onClick={this.handleSignInClick}
                                                        name="sign-in"
                                                        size="large"
                                                    />
                                                </List.Item>
                                            )
                                        })
                                    }
                                </List>
                            </Segment>
                        </Grid.Column>
                        <Grid.Column>
                            <Header icon>
                                <Icon name='settings' />
                                Sign-In Details
                                <Header.Subheader>
                                    Check your sign-in settings and set preferences.
                                </Header.Subheader>
                            </Header>
                            <Segment.Group>
                                <Segment textAlign='left'>
                                    <Header as="h3" textAlign="left">Account Details</Header>
                                    <Grid columns={2} relaxed='very'>
                                        <Grid.Column>
                                            <div>
                                                <b>ID</b>
                                                <br />
                                                {selectedRole.account}
                                            </div>
                                            <br />
                                            <div>
                                                <b>Name</b>
                                                <br />
                                                {selectedRole.role}
                                            </div>
                                            <br />
                                            <div>
                                                <b>Aliases</b>
                                                <br />
                                                <Label>alias-1</Label>
                                                <Label>alias-2</Label>
                                            </div>
                                        </Grid.Column>
                                        <Grid.Column>
                                            <div>
                                                <b>Environment</b>
                                                <br />
                                                N/A
                                            </div>
                                            <br />
                                            <div>
                                                <b>Sensitive</b>
                                                <br />
                                                N/A
                                            </div>
                                            <br />
                                        </Grid.Column>
                                    </Grid>
                                </Segment>
                                <Segment textAlign='left'>
                                    <Header as="h3" textAlign="left">Role Details</Header>
                                    <p>
                                        <b>Arn</b>
                                        <br />
                                        {selectedRole.arn}
                                    </p>
                                    <p>
                                        <b>Permissions</b>
                                        <br />
                                        {
                                            selectedRole.role != 'N/A'
                                                ? <a href="#">{selectedRole.role + ".json"}</a>
                                                : 'N/A'
                                        }
                                    </p>
                                    <p>
                                        <b>Per-user Role</b>
                                        <br />
                                        disabled
                                    </p>
                                </Segment>
                                <Segment>
                                    <Button primary content="Enable Per-User Role" />
                                </Segment>
                            </Segment.Group>
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
                <Divider vertical></Divider>
            </Segment>
        );
    }
}

export default Main;