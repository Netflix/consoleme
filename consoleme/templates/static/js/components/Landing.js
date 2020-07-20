import _ from 'lodash';
import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {
    Dropdown,
    Header,
    Icon,
    Input,
    Pagination,
    Segment,
    Table,
} from 'semantic-ui-react';
import ReactMarkdown from "react-markdown";

const WAIT_INTERVAL = 500;

const tableData = [
    { account_name: 'application_prod', account_id: 222233334444, role: 'admin', environment: "prod", },
    { account_name: 'application_test', account_id: 111122223333, role: 'admin', environment: "test", },
    { account_name: 'management', account_id: 555511112222, role: 'admin', environment: "prod", },
    { account_name: 'managementtest', account_id: 444422224444, role: 'admin', environment: "test", },
];

const accountNames = [
    { key: 'application_prod', value: 'application_prod', flag: 'application_prod', text: 'application_prod' },
    { key: 'application_test', value: 'application_test', flag: 'application_test', text: 'application_test' },
    { key: 'management', value: 'management', flag: 'management', text: 'management' },
    { key: 'managementtest', value: 'managementtest', flag: 'managementtest', text: 'managementtest' },
];

const environments = [
    { key: 'prod', value: 'prod', flag: 'prod', text: 'prod' },
    { key: 'test', value: 'test', flag: 'test', text: 'test' },
];

const roles = [
    { key: 'admin', value: 'admin', flag: 'admin', text: 'admin' },
    { key: 'user', value: 'user', flag: 'user', text: 'user' },
];

class LandingPage extends Component {
    state = {
        config: null,
        column: null,
        data: tableData,
        direction: 'descending',
        value: '',
    };

    componentDidMount() {
        this.timer = null;
        // TODO(heewonk), load configuration and eligible roles
    }

    handleSort = (clickedColumn) => () => {
        const { column, data, direction } = this.state;

        if (column !== clickedColumn) {
            return this.setState({
                column: clickedColumn,
                data: _.sortBy(data, [clickedColumn]),
                direction: 'ascending',
            });
        }

        this.setState({
            data: data.reverse(),
            direction: direction === 'ascending' ? 'descending' : 'ascending',
        });
    }

    handleRowExpansion = (idx) => () => {
        const { data } = this.state;

        let newData = [...data];
        if (newData[idx + 1] != null && 'raw' in newData[idx + 1]) {
            newData.splice(idx + 1, 1);
        } else {
            newData.splice(idx + 1, 0, { raw: newData[idx], })
        }

        return this.setState({
            data: newData,
        });
    }

    triggerChange() {
        const {value} = this.state;
        // send value to the backend
        console.log("Triggered", value);
    }

    handleInputChange(e, {value}) {
        clearTimeout(this.timer);
        this.setState({ value });
        this.timer = setTimeout(this.triggerChange.bind(this), WAIT_INTERVAL);
    }

    render() {
        const { data, direction, value } = this.state;

        return (
            <Segment basic>
                <Header as="h2">
                    Choose an account to access AWS Console
                </Header>
                <ReactMarkdown
                    linkTarget="_blank"
                    source={`Here you can find your available accounts that are allowed to access its AWS Console. Please refer to this [link](https://manuals.netflix.net/view/consoleme/mkdocs/master/) for more guides.`}
                />
                <Table sortable celled compact>
                    <Table.Header>
                        <Table.Row>
                            <Table.HeaderCell />
                            <Table.HeaderCell
                                onClick={this.handleSort('name')}
                                sorted={direction}
                            >
                                <Dropdown
                                    clearable
                                    placeholder='Account Name'
                                    search
                                    selection
                                    options={accountNames}
                                />
                            </Table.HeaderCell>
                            <Table.HeaderCell
                                sorted={direction}
                                onClick={this.handleSort('id')}
                            >
                                <Input
                                    onClick={(e) => e.stopPropagation()}
                                    onChange={this.handleInputChange.bind(this)}
                                    placeholder="Account ID"
                                    type="text"
                                    name="account_id"
                                    value={value}
                                />
                            </Table.HeaderCell>
                            <Table.HeaderCell
                                sorted={direction}
                                onClick={this.handleSort('environment')}
                            >
                                <Dropdown
                                    clearable
                                    placeholder='Environment'
                                    search
                                    selection
                                    options={environments}
                                />
                            </Table.HeaderCell>
                            <Table.HeaderCell
                                sorted={direction}
                                onClick={this.handleSort('roles')}
                            >
                                <Dropdown
                                    clearable
                                    placeholder='Roles'
                                    search
                                    selection
                                    options={roles}
                                />
                            </Table.HeaderCell>
                            <Table.HeaderCell>
                                CLI
                            </Table.HeaderCell>
                            <Table.HeaderCell>
                                Console
                            </Table.HeaderCell>
                        </Table.Row>
                    </Table.Header>
                    <Table.Body>
                        {
                            data.map((value, idx) => {
                                // if a row is clicked then show its associated detail row.
                                if ('raw' in value) {
                                    return (
                                        <Table.Row
                                            key={value.raw.account_name + "_detail"}
                                        >
                                            <Table.Cell colSpan="7">
                                                <pre>
                                                    {JSON.stringify(value.raw, null, 4)}
                                                </pre>
                                            </Table.Cell>
                                        </Table.Row>
                                    )
                                }

                                const {account_name, account_id, role, environment} = value;

                                return (
                                    <Table.Row
                                        key={account_name}
                                    >
                                        <Table.Cell
                                            collapsing
                                        >
                                            <Icon
                                                link
                                                name="caret down"
                                                onClick={this.handleRowExpansion(idx)}
                                            />
                                        </Table.Cell>
                                        <Table.Cell>{account_name}</Table.Cell>
                                        <Table.Cell>{account_id}</Table.Cell>
                                        <Table.Cell>{environment}</Table.Cell>
                                        <Table.Cell>{role}</Table.Cell>
                                        <Table.Cell>
                                            <Icon
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    console.log("CLI: ", e);
                                                }}
                                                link
                                                name="key"
                                            />
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Icon
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    console.log("SIGN-IN: ", e);
                                                }}
                                                link
                                                name="sign-in"
                                            />
                                        </Table.Cell>
                                    </Table.Row>
                                );
                            })
                        }
                    </Table.Body>
                    <Table.Footer>
                        <Table.Row>
                            <Table.HeaderCell colSpan='7'>
                                <Pagination floated="right" defaultActivePage={1} totalPages={3} />
                            </Table.HeaderCell>
                        </Table.Row>
                    </Table.Footer>
                </Table>
            </Segment>
        );
    }
}

export function renderLandingPage() {
    ReactDOM.render(
        <LandingPage />,
        document.getElementById("landing"),
    );
}

export default LandingPage;
