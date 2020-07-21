import React, {Component} from 'react'
import _ from 'lodash'

import ReactDOM from 'react-dom'
import {sendRequestCommon} from '../helpers/utils'
import {Dropdown, Header, Icon, Input, Pagination, Segment, Table} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";

function maybeParseJsonString(str) {
    try {
        return JSON.parse(str)
    } catch (e) {
        return str
    }
}

function ExpandNestedJson(data) {
    const keys = Object.keys(data)
    keys.forEach(function (item, index) {
        data[item] = maybeParseJsonString(data[item])
    })
    return data
}

class ConsoleMeDataTable extends Component {
    constructor(props) {
        super(props);
        this.state = {
            configEndpoint: props.configEndpoint,
            queryString: props.queryString,
            data: [],
            filteredData: [],
            tableConfig: {
                totalRows: 1000,
                rowsPerPage: 50,
                columns: [],
                direction: "descending",
                serverSideFiltering: true,
                dataEndpoint: '',
                tableName: '',
                tableDescription: '',
            }, // Default tableConfiguration can be specified here
            columns: [],
            value: "",
            loading: false,
            filters: {},
            activePage: 1
        };
        this.generateRows = this.generateRows.bind(this)
    }

    async componentDidMount() {
        this.setState({loading: true})
        this.timer = null;
        const configRequest = await fetch(this.state.configEndpoint)
        const tableConfig = await configRequest.json()
        this.setState({tableConfig: tableConfig})
        if (tableConfig.dataEndpoint) {
            const data = await sendRequestCommon({limit: tableConfig.totalRows}, tableConfig.dataEndpoint)
            this.setState({data: data})
            // Todo: Support filtering based on query parameters
            this.setState({filteredData: data})
        }
        this.setState({loading: false})
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
            newData.splice(idx + 1, 0, {raw: ExpandNestedJson(newData[idx])});
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

        return columnOptions;
    }

    generateColumns() {
        const {tableConfig, filters} = this.state;
        const columnOptions = this.generateColumnOptions();
        let columns = [];
        tableConfig.columns &&
        tableConfig.columns.forEach(
            function (item, index) {
                let key = item.key;
                const options = columnOptions[item.key];
                let columnCell
                switch (item.type) {
                    case "dropdown": {
                        columnCell = <Dropdown
                            name={item.key}
                            clearable
                            placeholder={item.placeholder}
                            search
                            selection
                            options={options}
                            onChange={this.filterColumn.bind(this)}
                        />
                    }
                    case "input": {
                        columnCell = <Input
                            name={item.key}
                            placeholder={item.placeholder}
                            onChange={this.filterColumn.bind(this)}
                            value={'' || filters[item.name]}
                        />
                    }
                }
                columns.push(
                    <Table.HeaderCell
                        onClick={this.handleSort(key)}
                        sorted={tableConfig.direction}
                    >
                        {columnCell}
                    </Table.HeaderCell>
                );
            }.bind(this)
        );
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

    generateRows() {
        const {filteredData, tableConfig, activePage} = this.state
        const filteredDataPaginated = filteredData.slice(
            (activePage-1) * tableConfig.rowsPerPage,
            activePage * tableConfig.rowsPerPage
        )
        return filteredDataPaginated.map((entry, idx) => {
            // if a row is clicked then show its associated detail row.
            if ("raw" in entry) {
                return (
                    <Table.Row>
                        <Table.Cell colSpan="7">
                            <pre>{JSON.stringify(entry.raw, null, 4)}</pre>
                        </Table.Cell>
                    </Table.Row>
                );
            }
            let cells = []
            // Iterate through our configured columns
            tableConfig.columns.forEach(
                function (column, index) {
                    cells.push(<Table.Cell>
                        <ReactMarkdown
                            linkTarget="_blank"
                            source={'' || entry[column.key].toString()}
                        />
                    </Table.Cell>)
                }
            )

            return (
                <Table.Row>
                    <Table.Cell collapsing>
                        <Icon
                            link
                            name="caret right"
                            onClick={this.handleRowExpansion(idx)}
                        />
                    </Table.Cell>
                    {/*{cells.map((cell, idx) => {return cell})}*/}
                    {cells}
                    {/*<Table.Cell>{account_name}</Table.Cell>*/}
                    {/*<Table.Cell>{account_id}</Table.Cell>*/}
                    {/*<Table.Cell>{environment}</Table.Cell>*/}
                    {/*<Table.Cell>{role}</Table.Cell>*/}
                    {/*<Table.Cell>*/}
                    {/*    <Icon*/}
                    {/*        onClick={e => {*/}
                    {/*            e.stopPropagation();*/}
                    {/*            console.log("CLI: ", e);*/}
                    {/*        }}*/}
                    {/*        link*/}
                    {/*        name="key"*/}
                    {/*    />*/}
                    {/*</Table.Cell>*/}
                    {/*<Table.Cell>*/}
                    {/*    <Icon*/}
                    {/*        onClick={e => {*/}
                    {/*            e.stopPropagation();*/}
                    {/*            console.log("SIGN-IN: ", e);*/}
                    {/*        }}*/}
                    {/*        link*/}
                    {/*        name="sign-in"*/}
                    {/*    />*/}
                    {/*</Table.Cell>*/}
                </Table.Row>
            );

        })
    }

    render() {
        {
        }
        const {filteredData, direction, value, tableConfig, activePage} = this.state;

        return (
            <Segment basic>
                <Header as="h2">{tableConfig.tableName}</Header>
                <ReactMarkdown
                    linkTarget="_blank"
                    source={tableConfig.tableDescription}
                    //source={`Here you can find your available accounts that are allowed to access its AWS Console. Please refer to this [link](https://manuals.netflix.net/view/consoleme/mkdocs/master/) for more guides.`}
                />
                <Table sortable celled compact selectable striped>
                    {this.generateColumns()}
                    <Table.Body>
                        {this.generateRows()}
                    </Table.Body>
                    <Table.Footer>
                        <Table.Row>
                            <Table.HeaderCell colSpan="7">
                                <Pagination
                                    floated="right"
                                    defaultActivePage={activePage}
                                    totalPages={parseInt(filteredData.length / tableConfig.rowsPerPage)}
                                    onPageChange={(event, data) => {
                                        this.setState({activePage: data.activePage})
                                    }
                                    }
                                />
                            </Table.HeaderCell>
                        </Table.Row>
                    </Table.Footer>
                </Table>
            </Segment>
        );
    }
}


export function renderDataTable(configEndpoint) {
    ReactDOM.render(
        <ConsoleMeDataTable configEndpoint={configEndpoint}/>,
        document.getElementById('datatable')
    )
}

export default ConsoleMeDataTable
