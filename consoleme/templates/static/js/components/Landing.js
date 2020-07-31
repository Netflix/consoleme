import _ from "lodash";
import React, {Component} from "react";
import ReactDOM from "react-dom";
import {
    Dropdown,
    Header,
    Icon,
    Pagination,
    Segment,
    Table
} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";

const WAIT_INTERVAL = 500;

const tableData = [
    {
        account_name: "application_prod",
        account_id: "222233334444",
        role: "admin",
        environment: "prod"
    },
    {
        account_name: "application_test",
        account_id: "111122223333",
        role: "admin",
        environment: "test"
    },
    {
        account_name: "management",
        account_id: "555511112222",
        role: "admin",
        environment: "prod"
    },
    {
        account_name: "managementtest",
        account_id: "444422224444",
        role: "admin",
        environment: "test"
    }
];

const tableConfig = {
    serverSideFiltering: false,
    dataEndpoint: '',
    columns: [
        {
            key: "account_name",
            placeholder: "Account Name",
            type: "dropdown",
            options: []
        },
        {
            key: "account_id",
            placeholder: "Account ID",
            type: "dropdown",
            options: []
        },
        {
            key: "environment",
            placeholder: "Environment",
            type: "dropdown",
            options: []
        },
        {
            key: "role",
            placeholder: "Roles",
            type: "dropdown",
            options: []
        }
    ]
};

class LandingPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            configEndpoint: props.configEndpoint,
            data: [],
            filteredData: [],
            tableConfig: {
                columns: [],
                direction: "descending",
                serverSideFiltering: false
            }, // Default tableConfiguration can be specified here
            columns: [],
            value: "",
            loading: false,
            filters: {}
        };
    }

    componentDidMount() {
        this.timer = null;
        // TODO(heewonk), load configuration and eligible roles
        this.setState({data: tableData});
        this.setState({filteredData: tableData});
        this.setState({tableConfig: tableConfig});
    }

    handleSort = clickedColumn => () => {
        const {column, data, direction} = this.state;

        if (column !== clickedColumn) {
            return this.setState({
                column: clickedColumn,
                data: _.sortBy(data, [clickedColumn]),
                direction: "ascending"
            });
        }

        this.setState({
            data: data.reverse(),
            direction: direction === "ascending" ? "descending" : "ascending"
        });
    };

    handleRowExpansion = idx => () => {
        const {filteredData} = this.state;

        let newData = [...filteredData];
        if (newData[idx + 1] != null && "raw" in newData[idx + 1]) {
            newData.splice(idx + 1, 1);
        } else {
            newData.splice(idx + 1, 0, {raw: newData[idx]});
        }

        return this.setState({
            filteredData: newData
        });
    };

    triggerChange() {
        const {value} = this.state;
        // send value to the backend
        console.log("Triggered", value);
    }

    handleInputChange(e, {value}) {
        clearTimeout(this.timer);
        this.setState({value});
        this.timer = setTimeout(this.triggerChange.bind(this), WAIT_INTERVAL);
    }

    generateColumnOptions() {
        const {data} = this.state;
        let columnOptionSet = {};
        // Iterate through our data
        data.forEach(function (item, index) {
            // Look at the key, value pairs in each row
            for (const [key, value] of Object.entries(item)) {
                // Create an empty set for the key if it doesn't already exist in columnOptions
                !(key in columnOptionSet) && (columnOptionSet[key] = new Set());
                columnOptionSet[key].add(value);
            }
        });

        let columnOptions = {};
        for (const [key, value] of Object.entries(columnOptionSet)) {
            value.forEach(function (item, index) {
                !(key in columnOptions) && (columnOptions[key] = []);
                columnOptions[key].push({
                    key: item,
                    value: item,
                    flag: item,
                    text: item
                });
            });
        }

        console.log(columnOptions);

        return columnOptions;
    }

    generateColumns() {
        const {tableConfig} = this.state;
        const columnOptions = this.generateColumnOptions();
        let columns = [];
        tableConfig.columns &&
        tableConfig.columns.forEach(
            function (item, index) {
                let key = item.key;
                const options = columnOptions[item.key];
                // console.log([] && Array.from(options))
                columns.push(
                    <Table.HeaderCell
                        onClick={this.handleSort(key)}
                        sorted={tableConfig.direction}
                    >
                        <Dropdown
                            name={item.key}
                            clearable
                            placeholder={item.placeholder}
                            search
                            selection
                            options={options}
                            onChange={this.filterColumn.bind(this)}
                        />
                    </Table.HeaderCell>
                );
            }.bind(this)
        );
        // this.setState({columns: columns})
        return (
            <Table.Header>
                <Table.Row>
                    <Table.HeaderCell/>
                    {columns}
                </Table.Row>
            </Table.Header>
        );
    }

    async filterColumnServerSide(event, filters) {
        const {tableConfig} = this.state;
        const data = await sendRequestCommon(
            {filters: filters},
            tableConfig.dataEndpoint
        );

        this.setState({
            filteredData: data,
            limit: tableConfig.totalRows,
            loading: false
        });
    }

    async filterColumn(event, data) {
        this.setState({loading: true});
        const {name, value} = data;
        const {tableConfig} = this.state;
        let filters = this.state.filters;
        filters[name] = value;
        this.setState({filters: filters});
        if (tableConfig.serverSideFiltering) {
            await this.filterColumnServerSide(event, filters);
        } else {
            await this.filterColumnClientSide(event, filters);
        }
    }

    async filterColumnClientSide(event, filters) {
        let {data, tableConfig, filteredData} = this.state;
        filteredData = data.filter(function (item) {
            for (let key in filters) {
                let re = filters[key];
                console.log("re ", re);
                try {
                    re = new RegExp(filters[key], "g");
                } catch (e) {
                    // Invalid Regex. Ignore
                }

                if (
                    item[key] === undefined ||
                    item[key] === "" ||
                    !String(item[key]).match(re)
                ) {
                    return false;
                }
            }
            return true;
        });
        console.log(filteredData);
        this.setState({filteredData: filteredData, loading: false});
    }

    render() {
        const {filteredData, direction, value} = this.state;

        return (
            <Segment basic>
                <Header as="h2">Choose an account to access AWS Console</Header>
                <ReactMarkdown
                    linkTarget="_blank"
                    source={`Here you can find your available accounts that are allowed to access its AWS Console. Please refer to this [link](https://manuals.netflix.net/view/consoleme/mkdocs/master/) for more guides.`}
                />
                <Table sortable celled compact selectable>
                    {this.generateColumns()}
                    <Table.Body>
                        {filteredData.map((value, idx) => {
                            // if a row is clicked then show its associated detail row.
                            if ("raw" in value) {
                                return (
                                    <Table.Row key={value.raw.account_name + "_detail"}>
                                        <Table.Cell colSpan="7">
                                            <pre>{JSON.stringify(value.raw, null, 4)}</pre>
                                        </Table.Cell>
                                    </Table.Row>
                                );
                            }

                            const {account_name, account_id, role, environment} = value;

                            return (
                                <Table.Row key={account_name}>
                                    <Table.Cell collapsing>
                                        <Icon
                                            link
                                            name="caret right"
                                            onClick={this.handleRowExpansion(idx)}
                                        />
                                    </Table.Cell>
                                    <Table.Cell>{account_name}</Table.Cell>
                                    <Table.Cell>{account_id}</Table.Cell>
                                    <Table.Cell>{environment}</Table.Cell>
                                    <Table.Cell>{role}</Table.Cell>
                                    <Table.Cell>
                                        <Icon
                                            onClick={e => {
                                                e.stopPropagation();
                                                console.log("CLI: ", e);
                                            }}
                                            link
                                            name="key"
                                        />
                                    </Table.Cell>
                                    <Table.Cell>
                                        <Icon
                                            onClick={e => {
                                                e.stopPropagation();
                                                console.log("SIGN-IN: ", e);
                                            }}
                                            link
                                            name="sign-in"
                                        />
                                    </Table.Cell>
                                </Table.Row>
                            );
                        })}
                    </Table.Body>
                    <Table.Footer>
                        <Table.Row>
                            <Table.HeaderCell colSpan="7">
                                <Pagination
                                    floated="right"
                                    defaultActivePage={1}
                                    totalPages={3}
                                />
                            </Table.HeaderCell>
                        </Table.Row>
                    </Table.Footer>
                </Table>
            </Segment>
        );
    }
}

export function renderLandingPage() {
    ReactDOM.render(<LandingPage/>, document.getElementById("landing"));
}

export default LandingPage;