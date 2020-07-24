import _ from 'lodash';
import qs from 'qs';
import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {sendRequestCommon} from '../helpers/utils';
import {Dropdown, Header, Icon, Input, Pagination, Segment, Table} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import SemanticDatepicker from 'react-semantic-ui-datepickers';
import 'react-semantic-ui-datepickers/dist/react-semantic-ui-datepickers.css';



const expandNestedJson = (data) => {
    Object.keys(data).forEach((key) => {
        try {
            data[key] = JSON.parse(data[key]);
        } catch (e) {
            data[key] = data[key];
        }
    });
    return data;
};


// TODO: Calendar

class ConsoleMeDataTable extends Component {
    constructor(props) {
        super(props);
        const {configEndpoint, queryString} = props;
        this.state = {
            configEndpoint,
            queryString,
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
            activePage: 1,
            expandedRow: null,
        };

        this.generateRows = this.generateRows.bind(this)
        this.generateFilterFromQueryString = this.generateFilterFromQueryString.bind(this)
    }

    async componentDidMount() {
        this.timer = null;
        this.setState({
            loading: true,
        }, async () => {
            const request = await fetch(this.state.configEndpoint);
            const tableConfig = await request.json();

            let data = [];
            if (tableConfig.dataEndpoint) {
                data = await sendRequestCommon({
                    limit: tableConfig.totalRows,
                }, tableConfig.dataEndpoint);
            }

            // TODO, Support filtering based on query parameters
            this.setState({
                data,
                filteredData: data,
                loading: false,
                tableConfig,
            }, async () => {
                await this.generateFilterFromQueryString();
            });
        });
    }

    handleSort = clickedColumn => () => {
        const {column, filteredData, direction} = this.state;

        if (column !== clickedColumn) {
            return this.setState({
                column: clickedColumn,
                filteredData: _.sortBy(filteredData, [clickedColumn]),
                direction: "ascending"
            });
        }

        this.setState({
            filteredData: filteredData.reverse(),
            direction: direction === "ascending" ? "descending" : "ascending"
        });
    };

    handleRowExpansion = (idx) => () => {
        const {expandedRow, filteredData, tableConfig, activePage} = this.state;

        // close expansion if there is any expanded row.
        if (expandedRow && expandedRow.index === idx + 1) {
            this.setState({
                expandedRow: null,
            });
        } else {
            // expand the row if a row is clicked.
            const filteredDataPaginated = filteredData.slice(
                (activePage - 1) * tableConfig.rowsPerPage,
                activePage * tableConfig.rowsPerPage - 1
            );
            const newExpandedRow = {
                index: idx + 1,
                data: expandNestedJson(filteredDataPaginated[idx]),
            };
            this.setState({
                expandedRow: newExpandedRow,
            });
        }
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
        data.forEach((item) => {
            Object.keys(item).forEach((key) => {
                if (!(key in columnOptionSet)) {
                    columnOptionSet[key] = new Set();
                }
                columnOptionSet[key].add(item[key]);
            });
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
        const columns = [];

        (tableConfig.columns || []).forEach((item) => {
            let key = item.key;
            const options = columnOptions[item.key];
            let columnCell = null;

            switch (item.type) {
                case "dropdown": {
                    columnCell = (
                        <Dropdown
                            name={item.key}
                            clearable
                            placeholder={item.placeholder}
                            search
                            selection
                            options={options}
                            onChange={this.filterColumn.bind(this)}
                            value={filters[item.key] != null ? filters[item.key] : ''}
                            fluid
                        />
                    );
                    break;
                }
                case "input": {
                    columnCell = (
                        <Input
                            name={item.key}
                            autoComplete="off"
                            style={item.style}
                            placeholder={item.placeholder}
                            onChange={this.filterColumn.bind(this)}
                            value={filters[item.key] != null ? filters[item.key] : ''}
                        />
                    );
                    break
                }
                case "daterange": {
                    columnCell = <SemanticDatepicker name={item.key} onChange={this.filterDateRangeTime.bind(this)} type="range" />;

                    break
                }
            }

            columns.push(
                <Table.HeaderCell
                    style={item.style}
                    fluid
                    //onClick={this.handleSort(key)}
                    //sorted={tableConfig.direction}
                >
                    {columnCell}
                    <Icon
                        name={"sort"}
                        link
                        onClick={this.handleSort(key)}
                        sorted={tableConfig.direction} />
                </Table.HeaderCell>
            );
        });
        return (
            <Table.Header>
                <Table.Row>
                    <Table.HeaderCell/>
                    {columns}
                </Table.Row>
            </Table.Header>
        );
    }

    async generateFilterFromQueryString() {
        const {tableConfig, queryString} = this.state
        const filters = qs.parse(queryString, {ignoreQueryPrefix: true})
        if (filters) {
            this.setState({
                filters: filters
            });
        }

        if (tableConfig.serverSideFiltering) {
            await this.filterColumnServerSide({}, filters);
        } else {
            await this.filterColumnClientSide({}, filters);
        }
    }

    async filterDateRangeTime(event, data) {
        console.log(event)
        console.log(data)
        // Convert epoch milliseconds to epoch seconds
        if (data.value && data.value[0] && data.value[1]) {
            const startTime = parseInt(data.value[0].getTime() / 1000);
            const endTime = parseInt(data.value[1].getTime() / 1000);
            await this.filterColumn(_, {name: data.name, value: [startTime, endTime]})
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

    async filterColumnServerSide(event, filters) {
        const {tableConfig} = this.state;
        const data = await sendRequestCommon(
            {filters: filters},
            tableConfig.dataEndpoint
        );

        this.setState({
            expandedRow: null,
            filteredData: data,
            limit: tableConfig.totalRows,
            loading: false
        });
    }

    async filterColumnClientSide(event, filters) {
        const {data} = this.state;
        const filtered = data.filter((item) => {
            for (let key in filters) {
                let re = filters[key];
                try {
                    re = new RegExp(filters[key], "g");
                } catch (e) {
                    // Invalid Regex. Ignore
                }

                if (item[key] != null || !String(item[key]).match(re)) {
                    return false;
                }
            }
            return true;
        });

        this.setState({
            expandedRow: null,
            filteredData: filtered,
            loading: false
        });
    }

    generateRows() {
        const {expandedRow, filteredData, tableConfig, activePage} = this.state;
        const filteredDataPaginated = filteredData.slice(
            (activePage - 1) * tableConfig.rowsPerPage,
            activePage * tableConfig.rowsPerPage - 1
        );

        if (expandedRow) {
            const {index, data} = expandedRow;
            filteredDataPaginated.splice(index, 0, data);
        }

        return filteredDataPaginated.map((entry, idx) => {
            // if a row is clicked then show its associated detail row.
            if (expandedRow && expandedRow.index === idx) {
                return (
                    <Table.Row>
                        <Table.Cell collapsing colSpan={8}>
                            <pre>
                                {JSON.stringify(expandedRow.data, null, 4)}
                            </pre>
                        </Table.Cell>
                    </Table.Row>
                );
            }

            const cells = [];
            // Iterate through our configured columns
            tableConfig.columns.forEach((column) => {
                if (column.type === "daterange") {
                    cells.push(<Table.Cell collapsing>
                        <ReactMarkdown
                            linkTarget="_blank"
                            source={'' || new Date(entry[column.key] * 1000).toUTCString()}
                        />
                    </Table.Cell>)

                } else {
                    cells.push(<Table.Cell collapsing>
                        <ReactMarkdown
                            linkTarget="_blank"
                            source={'' || entry[column.key].toString()}
                        />
                    </Table.Cell>)
                }
            })

            return (
                <Table.Row>
                    <Table.Cell collapsing>
                        <Icon
                            link
                            name={(expandedRow && expandedRow.index - 1 === idx) ? "caret down" : "caret right"}
                            onClick={this.handleRowExpansion(idx)}
                        />
                    </Table.Cell>
                    {cells}
                </Table.Row>
            );
        });
    }

    render() {
        const {filteredData, tableConfig, activePage} = this.state;
        const columns = this.generateColumns();
        return (
            <Segment basic>
                <Header as="h2">{tableConfig.tableName}</Header>
                <ReactMarkdown
                    linkTarget="_blank"
                    source={tableConfig.tableDescription}
                />
                <Table collapsing sortable celled compact selectable striped>
                    {columns}
                    <Table.Body>
                        {this.generateRows()}
                    </Table.Body>
                    <Table.Footer>
                        <Table.Row>
                            <Table.HeaderCell colSpan={8}>
                                <Pagination
                                    floated="right"
                                    defaultActivePage={activePage}
                                    totalPages={parseInt(filteredData.length / tableConfig.rowsPerPage, 10)}
                                    onPageChange={(event, data) => {
                                        this.setState({
                                            activePage: data.activePage
                                        });
                                    }}
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
        <ConsoleMeDataTable
            configEndpoint={configEndpoint}
            queryString={queryString}
        />,
        document.getElementById('datatable'),
    );
}

export default ConsoleMeDataTable
