import React, {Component} from 'react'
import _ from 'lodash'
import ReactDOM from 'react-dom'
import {sendRequestCommon} from '../helpers/utils'
import {Dropdown, Header, Icon, Input, Pagination, Segment, Table} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
let qs = require('qs');

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
// TODO: Calendar

class ConsoleMeDataTable extends Component {
    constructor(props) {
        super(props);
        this.state = {
            configEndpoint: props.configEndpoint,
            queryString: props.queryString,
            data: [],
            filteredData: [],
            tableConfig: {
                expandableRows: true, // TODO: Hee Won - We should obey this configuration if possible
                sortable: true, // TODO: Figure out sorting logic for both frontend / backend
                totalRows: 1000,
                rowsPerPage: 50,
                columns: [],
                direction: "descending",
                serverSideFiltering: true,
                dataEndpoint: '',
                tableName: '',
                tableDescription: '',
            },
            columns: [],
            value: "",
            loading: false,
            filters: {},
            sort: {},
            activePage: 1
        };
        console.log(this.state)
        this.generateRows = this.generateRows.bind(this)
        this.generateFilterFromQueryString = this.generateFilterFromQueryString.bind(this)
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
        await this.generateFilterFromQueryString()
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

    handleRowExpansion(event, idx) {
        const {filteredData, tableConfig} = this.state;
        let newData = [...filteredData];
        if (newData[idx + 1] != null && "raw" in newData[idx + 1]) {
            newData.splice(idx + 1, 1);
            event.target.classList.remove("caret", "down")
            event.target.classList.add("caret", "right")
            tableConfig.rowsPerPage -= 1
            // TODO: Change caret icon

        } else {
            event.target.classList.remove("caret", "right")
            event.target.classList.add("caret", "down")
            tableConfig.rowsPerPage += 1
            newData.splice(idx + 1, 0, {raw: ExpandNestedJson(newData[idx])});
            // TODO: Change caret icon
        }
        this.setState({tableConfig: tableConfig})
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
                    case "dropdown":
                        columnCell = <Dropdown
                            name={item.key}
                            clearable
                            placeholder={item.placeholder}
                            search
                            selection
                            options={options}
                            onChange={this.filterColumn.bind(this)} // TODO: Hee Won - need debounce
                            defaultValue={'' || filters[item.key]}
                        />
                        break
                    case "input":
                        columnCell = <Input
                            name={item.key}
                            autoComplete="off"
                            placeholder={item.placeholder}
                            onChange={this.filterColumn.bind(this)} // TODO: Hee Won - need debounce
                            value={'' || filters[item.key]}
                        />
                        break
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

    async generateFilterFromQueryString() {
        const {tableConfig, queryString} = this.state
        const filters = qs.parse(queryString, { ignoreQueryPrefix: true })
        if (filters) {
            this.setState({filters: filters})
        }
        if (tableConfig.serverSideFiltering) {
            await this.filterColumnServerSide({}, filters);
        } else {
            await this.filterColumnClientSide({}, filters);
        }
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
                        <Table.Cell collapsing colSpan="7">
                            <pre>{JSON.stringify(entry.raw, null, 4)}</pre>
                        </Table.Cell>
                    </Table.Row>
                );
            }
            let cells = []
            // Iterate through our configured columns
            tableConfig.columns.forEach(
                function (column, index) {
                    cells.push(<Table.Cell collapsing>
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
                            onClick={(event) => this.handleRowExpansion(event, idx)} // TODO: Fix caret
                        />
                    </Table.Cell>
                    {cells}
                </Table.Row>
            );

        })
    }

    render() {
        const {filteredData, tableConfig, activePage} = this.state;

        return (
            <Segment basic>
                <Header as="h2">{tableConfig.tableName}</Header>
                <ReactMarkdown
                    linkTarget="_blank"
                    source={tableConfig.tableDescription}
                 />
                <Table collapsing sortable celled compact selectable striped>
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


export function renderDataTable(configEndpoint, queryString = "") {
    ReactDOM.render(
        <ConsoleMeDataTable configEndpoint={configEndpoint} queryString={queryString}/>,
        document.getElementById('datatable')
    )
}

export default ConsoleMeDataTable
