import _ from 'lodash';
import qs from 'qs';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import {
  Button, Dimmer, Dropdown, Header, Icon, Input, Label, Loader, Pagination, Segment, Table,
} from 'semantic-ui-react';
import ReactJson from 'react-json-view';
import ReactMarkdown from 'react-markdown';
import SemanticDatepicker from 'react-semantic-ui-datepickers';
import 'react-semantic-ui-datepickers/dist/react-semantic-ui-datepickers.css';
import { Redirect, BrowserRouter } from 'react-router-dom';
import PropTypes from 'prop-types';
import { sendRequestCommon } from '../helpers/utils';

const expandNestedJson = (data) => {
  Object.keys(data).forEach((key) => {
    try {
      data[key] = JSON.parse(data[key]);
    } catch (e) {
      // no-op
    }
  });
  return data;
};

class ConsoleMeDataTable extends Component {
  constructor(props) {
    super(props);
    const { configEndpoint, queryString } = props;
    this.state = {
      configEndpoint,
      queryString,
      redirect: false,
      data: [],
      filteredData: [],
      tableConfig: {
        expandableRows: true,
        sortable: true,
        totalRows: 1000,
        rowsPerPage: 50,
        columns: [],
        direction: 'descending',
        serverSideFiltering: true,
        dataEndpoint: '',
        tableName: '',
        tableDescription: '',
      },
      filters: {},
      loading: false,
      activePage: 1,
      expandedRow: null,
      direction: 'descending',
      debounceWait: 300,
      isLoading: false,
    };

    this.generateRows = this.generateRows.bind(this);
    this.generateFilterFromQueryString = this.generateFilterFromQueryString.bind(this);
    this.handleCellClick = this.handleCellClick.bind(this);
    this.renderRedirect = this.renderRedirect.bind(this);
    this.filterColumn = this.filterColumn.bind(this);
    this.filterDateRangeTime = this.filterDateRangeTime.bind(this);
  }

  async componentDidMount() {
    const { configEndpoint } = this.state;
    this.timer = null;
    this.setState({
      isLoading: true,
    }, async () => {
      const request = await fetch(configEndpoint);
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
        isLoading: false,
        tableConfig,
      }, async () => {
        await this.generateFilterFromQueryString();
      });
    });
  }

  calculateColumnSize() {
    const { tableConfig } = this.state;
    return (tableConfig.columns || []).length + (tableConfig.expandableRows ? 1 : 0);
  }

  handleSort(clickedColumn) {
    const { column, filteredData, direction } = this.state;

    if (column !== clickedColumn) {
      return this.setState({
        column: clickedColumn,
        filteredData: _.sortBy(filteredData, [clickedColumn]),
        direction: 'ascending',
      });
    }

    this.setState({
      filteredData: filteredData.reverse(),
      direction: direction === 'ascending' ? 'descending' : 'ascending',
    });
    return true;
  }

  handleRowExpansion(idx) {
    const {
      expandedRow, filteredData, tableConfig, activePage,
    } = this.state;

    // close expansion if there is any expanded row.
    if (expandedRow && expandedRow.index === idx + 1) {
      this.setState({
        expandedRow: null,
      });
    } else {
      // expand the row if a row is clicked.
      const filteredDataPaginated = filteredData.slice(
        (activePage - 1) * tableConfig.rowsPerPage,
        activePage * tableConfig.rowsPerPage - 1,
      );

      // get an offset if there is any expanded row and trying to expand row underneath
      const offset = (expandedRow && expandedRow.index < idx) ? 1 : 0;
      const newExpandedRow = {
        index: idx + 1 - offset,
        data: expandNestedJson(filteredDataPaginated[idx - offset]),
      };
      this.setState({
        expandedRow: newExpandedRow,
      });
    }
    return true;
  }

  generateColumnOptions() {
    const { data } = this.state;
    const columnOptionSet = {};

    // Iterate through our data
    data.forEach((item) => {
      Object.keys(item).forEach((key) => {
        if (!(key in columnOptionSet)) {
          columnOptionSet[key] = new Set();
        }
        columnOptionSet[key].add(item[key]);
      });
    });

    const columnOptions = {};
    for (const [key, value] of Object.entries(columnOptionSet)) {
      value.forEach((item) => {
        !(key in columnOptions) && (columnOptions[key] = []);
        columnOptions[key].push({
          key: item,
          value: item,
          flag: item,
          text: item,
        });
      });
    }

    return columnOptions;
  }

  generateColumns() {
    const { direction, tableConfig, filters } = this.state;
    const columnOptions = this.generateColumnOptions();
    const columns = [];

    (tableConfig.columns || []).forEach((item) => {
      const { key } = item;
      const options = columnOptions[item.key];
      let columnCell = null;

      switch (item.type) {
        case 'dropdown': {
          columnCell = (
            <Dropdown
              name={item.key}
              clearable
              placeholder={item.placeholder}
              search
              selection
              options={options}
              onChange={this.filterColumn}
              onClick={(e) => {
                e.stopPropagation();
              }}
              value={filters[item.key] != null ? filters[item.key] : ''}
            />
          );
          break;
        }
        case 'input': {
          columnCell = (
            <Input
              name={item.key}
              autoComplete="off"
              style={item.style}
              placeholder={item.placeholder}
              onChange={this.filterColumn}
              onClick={(e) => {
                e.stopPropagation();
              }}
              value={filters[item.key] != null ? filters[item.key] : ''}
            />
          );
          break;
        }
        case 'daterange': {
          columnCell = (
            <SemanticDatepicker
              name={item.key}
              onChange={this.filterDateRangeTime}
              onClick={(e) => {
                e.stopPropagation();
              }}
              type="range"
            />
          );
          break;
        }
        case 'button': {
          columnCell = (
            <Header
              as="h4"
              onClick={(e) => {
                e.stopPropagation();
              }}
            >
              {item.placeholder}
            </Header>
          );
          break;
        }
        case 'icon': {
          columnCell = (
            <Header
              as="h4"
              onClick={(e) => {
                e.stopPropagation();
              }}
            >
              {item.placeholder}
            </Header>
          );
          break;
        }
        default: {
          columnCell = (
            <Header
              as="h4"
              onClick={(e) => { e.stopPropagation(); }}
            >
              {item.placeholder}
            </Header>
          );
          break;
        }
      }

      columns.push(
        <Table.HeaderCell
          style={item.style}
          onClick={() => this.handleSort(key)}
          sorted={!(['button', 'icon'].includes(item.type)) ? direction : null}
          textAlign={item.type === 'button' ? 'center' : null}
        >
          {columnCell}
        </Table.HeaderCell>,
      );
    });
    return (
      <Table.Header>
        <Table.Row>
          {tableConfig.expandableRows && (
            <Table.HeaderCell />
          )}
          {columns}
        </Table.Row>
      </Table.Header>
    );
  }

  async generateFilterFromQueryString() {
    const { tableConfig, queryString } = this.state;
    const parsedQueryString = qs.parse(queryString, { ignoreQueryPrefix: true });
    const filters = {};
    if (parsedQueryString) {
      tableConfig.columns.forEach((column) => {
        if (parsedQueryString[column.key] != null && parsedQueryString[column.key]) {
          filters[column.key] = parsedQueryString[column.key];
        }
      });
    }

    this.setState({
      filters,
    });

    if (tableConfig.serverSideFiltering) {
      await this.filterColumnServerSide({}, filters);
    } else {
      this.filterColumnClientSide({}, filters);
    }
  }

  async filterDateRangeTime(event, data) {
    // Convert epoch milliseconds to epoch seconds
    if (data.value && data.value[0] && data.value[1]) {
      const startTime = parseInt(data.value[0].getTime() / 1000, 10);
      const endTime = parseInt(data.value[1].getTime() / 1000, 10);
      await this.filterColumn(_, { name: data.name, value: [startTime, endTime] });
    }
  }

  async filterColumn(event, data) {
    this.setState({ loading: true });
    const { name, value } = data;
    const { tableConfig } = this.state;

    const { filters } = this.state;
    filters[name] = value;
    this.setState({
      filters,
    });

    if (tableConfig.serverSideFiltering) {
      clearTimeout(this.timer);
      this.timer = setTimeout(
        async () => {
          await this.filterColumnServerSide({}, filters);
        },
        this.state.debounceWait,
      );
    } else {
      clearTimeout(this.timer);
      this.timer = setTimeout(
        () => {
          this.filterColumnClientSide(event, filters);
        },
        this.state.debounceWait,
      );
    }
  }

  async filterColumnServerSide(event, filters) {
    const { tableConfig } = this.state;
    const data = await sendRequestCommon(
      { filters },
      tableConfig.dataEndpoint,
    );

    this.setState({
      expandedRow: null,
      filteredData: data,
      loading: false,
    });
  }

  filterColumnClientSide(event, filters) {
    const { data } = this.state;
    let filtered = [];
    if (Object.keys(filters).length > 0) {
      filtered = data.filter((item) => {
        let isMatched = true;
        Object.keys(filters).map((key) => {
          const filter = filters[key];
          if (!filter) {
            return;
          }
          const re = new RegExp(filter, 'g');
          if (!re.test(item[key])) {
            isMatched = false;
          }
        });
        return isMatched;
      });
    } else {
      filtered = data;
    }

    this.setState({
      expandedRow: null,
      filteredData: filtered,
      loading: false,
      activePage: 1,
    });
  }

  handleCellClick(e, column, entry) {
    const { queryString } = this.state;
    // This function should appropriately handle a Cell Click given a desired
    // action by the column configuration
    if (column.onClick) {
      if (column.onClick.action === 'redirect') {
        this.setState({
          redirect: entry[column.key] + queryString,
        });
      }
    }
  }

  generateRows() {
    const {
      expandedRow, filteredData, tableConfig, activePage,
    } = this.state;
    const filteredDataPaginated = filteredData.slice(
      (activePage - 1) * tableConfig.rowsPerPage,
      activePage * tableConfig.rowsPerPage - 1,
    );

    if (expandedRow) {
      const { index, data } = expandedRow;
      filteredDataPaginated.splice(index, 0, data);
    }

    return filteredDataPaginated.map((entry, idx) => {
      // if a row is clicked then show its associated detail row.
      if (expandedRow && expandedRow.index === idx) {
        return (
          <Table.Row>
            <Table.Cell collapsing colSpan={this.calculateColumnSize()}>
              <ReactJson
                displayDataTypes={false}
                displayObjectSize={false}
                collapseStringsAfterLength={70}
                indentWidth={2}
                name={false}
                src={expandedRow.data}
              />
            </Table.Cell>
          </Table.Row>
        );
      }

      // TODO(heewonk), instead of rendering by column type,
      //  create separate component for these types
      const cells = [];
      tableConfig.columns.forEach((column) => {
        if (column.type === 'daterange') {
          cells.push(
            <Table.Cell collapsing>
              <ReactMarkdown
                linkTarget="_blank"
                source={'' || new Date(entry[column.key] * 1000).toUTCString()}
              />
            </Table.Cell>,
          );
        } else if (column.type === 'button') {
          cells.push(
            <Table.Cell collapsing>
              <Button
                content={entry[column.content] || column.content}
                fluid
                labelPosition="right"
                icon={column.icon}
                onClick={(e) => {
                  this.handleCellClick(e, column, entry);
                }}
                primary
                size="mini"
              />
            </Table.Cell>,
          );
        } else if (column.type === 'icon') {
          cells.push(
            <Table.Cell collapsing>
              <Icon
                onClick={(e) => {
                  this.handleCellClick(e, column, entry);
                }}
                link
                name={column.icon}
              />
            </Table.Cell>,
          );
        } else if (column.useLabel) {
          cells.push(
            <Table.Cell collapsing>
              <Label>
                {'' || entry[column.key].toString()}
              </Label>
            </Table.Cell>,
          );
        } else {
          cells.push(
            <Table.Cell collapsing>
              <ReactMarkdown
                linkTarget="_blank"
                source={'' || entry[column.key].toString()}
              />
            </Table.Cell>,
          );
        }
      });

      return (
        <Table.Row>
          {tableConfig.expandableRows
          && (
            <Table.Cell collapsing>
              <Icon
                link
                name={(expandedRow && expandedRow.index - 1 === idx) ? 'caret down' : 'caret right'}
                onClick={() => this.handleRowExpansion(idx)}
              />
            </Table.Cell>
          )}
          {cells}
        </Table.Row>
      );
    });
  }

  renderRedirect() {
    const { redirect } = this.state;
    if (redirect) {
      return <Redirect to={redirect} />;
    }
    return true;
  }

  render() {
    const {
      activePage,
      filteredData,
      isLoading,
      redirect,
      tableConfig,
    } = this.state;
    const totalPages = parseInt(filteredData.length / tableConfig.rowsPerPage, 10);
    const columns = this.generateColumns();

    if (isLoading) {
      return (
        <Segment basic>
          <Dimmer active inverted size="large">
            <Loader inverted content='Loading' />
          </Dimmer>
        </Segment>
      );
    }

    // TODO (heewonk), revisit following redirection logic when moving to SPA again
    if (redirect) {
      return (
        <BrowserRouter forceRefresh>
          {this.renderRedirect()}
        </BrowserRouter>
      );
    }

    return (
      <Segment basic>
        <Header as="h2">{tableConfig.tableName}</Header>
        <ReactMarkdown
          linkTarget="_blank"
          source={tableConfig.tableDescription}
          escapeHtml={false}
        />
        <Table collapsing sortable celled compact selectable striped>
          {columns}
          <Table.Body>
            {this.generateRows()}
          </Table.Body>
          <Table.Footer>
            <Table.Row>
              <Table.HeaderCell collapsing colSpan={this.calculateColumnSize()}>
                { totalPages > 0
                  ? (
                    <Pagination
                      floated="right"
                      defaultActivePage={activePage}
                      totalPages={totalPages}
                      onPageChange={(event, data) => {
                        this.setState({
                          activePage: data.activePage,
                          expandedRow: null,
                        });
                      }}
                    />
                  ) : ''}
              </Table.HeaderCell>
            </Table.Row>
          </Table.Footer>
        </Table>
      </Segment>
    );
  }
}

ConsoleMeDataTable.propTypes = {
  configEndpoint: PropTypes.element.isRequired,
  queryString: PropTypes.string,
};

ConsoleMeDataTable.defaultProps = {
  queryString: '',
};

export function renderDataTable(configEndpoint, queryString = '') {
  ReactDOM.render(
    <ConsoleMeDataTable
      configEndpoint={configEndpoint}
      queryString={queryString}
    />,
    document.getElementById('datatable'),
  );
}

export default ConsoleMeDataTable;
