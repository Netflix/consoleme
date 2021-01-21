import _ from "lodash";
import qs from "qs";
import React, { Component } from "react";
import {
  Button,
  Dimmer,
  Dropdown,
  Header,
  Icon,
  Input,
  Label,
  Loader,
  Message,
  Pagination,
  Segment,
  Table,
} from "semantic-ui-react";
import ReactJson from "react-json-view";
import ReactMarkdown from "react-markdown";
import SemanticDatepicker from "react-semantic-ui-datepickers";
import "react-semantic-ui-datepickers/dist/react-semantic-ui-datepickers.css";
import { Link, Redirect, BrowserRouter } from "react-router-dom";

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

const initialState = {
  redirect: false,
  data: [],
  filteredData: [],
  tableConfig: {
    expandableRows: true,
    sortable: true,
    totalRows: 1000,
    rowsPerPage: 50,
    columns: [],
    direction: "descending",
    serverSideFiltering: true,
    dataEndpoint: "",
    tableName: "",
    tableDescription: "",
  },
  filters: {},
  activePage: 1,
  expandedRow: null,
  direction: "descending",
  debounceWait: 500,
  isLoading: false,
  warningMessage: "",
};

class ConsoleMeDataTable extends Component {
  constructor(props) {
    super(props);
    const { config } = props;
    this.state = {
      ...initialState,
      tableConfig: config,
    };
    this.timer = null;
    this.generateRows = this.generateRows.bind(this);
    this.generateFilterFromQueryString = this.generateFilterFromQueryString.bind(
      this
    );
    this.handleCellClick = this.handleCellClick.bind(this);
    this.renderRedirect = this.renderRedirect.bind(this);
    this.filterColumn = this.filterColumn.bind(this);
    this.filterDateRangeTime = this.filterDateRangeTime.bind(this);
    this.generateMessagesFromQueryString = this.generateMessagesFromQueryString.bind(
      this
    );
  }

  async componentDidMount() {
    const { tableConfig } = this.state;

    this.setState(
      {
        isLoading: true,
      },
      async () => {
        let data = await this.props.sendRequestCommon(
          {
            limit: tableConfig.totalRows,
          },
          tableConfig.dataEndpoint
        );

        if (!data) {
          return;
        }

        // This means it raised an exception from fetching data
        if (data.status) {
          data = [];
        }

        this.setState(
          {
            data,
            filteredData: data,
            isLoading: false,
          },
          async () => {
            await this.generateFilterFromQueryString();
            await this.generateMessagesFromQueryString();
          }
        );
      }
    );
  }

  calculateColumnSize() {
    const { tableConfig } = this.state;
    return (
      (tableConfig.columns || []).length + (tableConfig.expandableRows ? 1 : 0)
    );
  }

  handleSort(clickedColumn) {
    const { column, filteredData, direction } = this.state;

    if (column !== clickedColumn) {
      return this.setState({
        column: clickedColumn,
        filteredData: _.sortBy(filteredData, [clickedColumn]),
        direction: "ascending",
      });
    }

    this.setState({
      filteredData: filteredData.reverse(),
      direction: direction === "ascending" ? "descending" : "ascending",
    });
    return true;
  }

  handleRowExpansion(idx) {
    const { expandedRow, filteredData, tableConfig, activePage } = this.state;

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

      // get an offset if there is any expanded row and trying to expand row underneath
      const offset = expandedRow && expandedRow.index < idx ? 1 : 0;
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
    const { data = [] } = this.state;
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
      const options = columnOptions[item.key] || [];
      let columnCell = null;

      switch (item.type) {
        case "dropdown": {
          columnCell = (
            <Dropdown
              name={item.key}
              style={item.style}
              clearable
              placeholder={item.placeholder}
              search
              selection
              compact
              options={options}
              onChange={this.filterColumn}
              onClick={(e) => {
                e.stopPropagation();
              }}
              value={filters[item.key] != null ? filters[item.key] : ""}
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
              onChange={this.filterColumn}
              onClick={(e) => {
                e.stopPropagation();
              }}
              value={filters[item.key] != null ? filters[item.key] : ""}
            />
          );
          break;
        }
        case "link": {
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
              value={filters[item.key] != null ? filters[item.key] : ""}
            />
          );
          break;
        }
        case "daterange": {
          columnCell = (
            <SemanticDatepicker
              name={item.key}
              style={item.style}
              onChange={this.filterDateRangeTime}
              onClick={(e) => {
                e.stopPropagation();
              }}
              type="range"
              compact
            />
          );
          break;
        }
        case "button": {
          columnCell = (
            <Header
              as="h4"
              style={item.style}
              onClick={(e) => {
                e.stopPropagation();
              }}
            >
              {item.placeholder}
            </Header>
          );
          break;
        }
        case "icon": {
          columnCell = (
            <Header
              as="h4"
              style={item.style}
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
            <Label
              style={item.style}
              color={item.color}
              onClick={(e) => {
                e.stopPropagation();
              }}
              basic
            >
              {item.placeholder}
            </Label>
          );
          break;
        }
      }

      columns.push(
        <Table.HeaderCell
          key={key}
          style={item.style}
          width={item.width}
          onClick={() => this.handleSort(key)}
          sorted={!["button"].includes(item.type) ? direction : null}
          textAlign={item.type === "button" ? "center" : null}
        >
          {columnCell}
        </Table.HeaderCell>
      );
    });
    return (
      <Table.Header>
        <Table.Row>
          {tableConfig.expandableRows && <Table.HeaderCell />}
          {columns}
        </Table.Row>
      </Table.Header>
    );
  }

  async generateMessagesFromQueryString() {
    const parsedQueryString = qs.parse(window.location.search, {
      ignoreQueryPrefix: true,
    });
    if (parsedQueryString) {
      Object.keys(parsedQueryString).forEach((key) => {
        if (key === "warningMessage") {
          this.setState({
            warningMessage: atob(parsedQueryString[key]),
          });
        }
      });
    }
  }

  async generateFilterFromQueryString() {
    const { tableConfig } = this.state;
    const parsedQueryString = qs.parse(window.location.search, {
      ignoreQueryPrefix: true,
    });
    const filters = {};
    if (parsedQueryString) {
      Object.keys(parsedQueryString).forEach((key) => {
        filters[key] = parsedQueryString[key];
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
      await this.filterColumn(_, {
        name: data.name,
        value: [startTime, endTime],
      });
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
      this.timer = setTimeout(async () => {
        await this.filterColumnServerSide({}, filters);
      }, this.state.debounceWait);
    } else {
      clearTimeout(this.timer);
      this.timer = setTimeout(() => {
        this.filterColumnClientSide(event, filters);
      }, this.state.debounceWait);
    }
  }

  async filterColumnServerSide(event, filters) {
    const { tableConfig } = this.state;
    let filteredData = await this.props.sendRequestCommon(
      { filters },
      tableConfig.dataEndpoint
    );

    if (!filteredData) {
      return;
    }

    if (filteredData.status) {
      filteredData = [];
    }

    this.setState({
      expandedRow: null,
      filteredData,
      loading: false,
      activePage: 1,
    });
  }

  filterColumnClientSide(event, filters) {
    const { data } = this.state;
    let filtered = [];
    if (Object.keys(filters).length > 0) {
      filtered = data.filter((item) => {
        let isMatched = true;
        Object.keys(filters).forEach((key) => {
          const filter = filters[key];
          if (!filter) {
            isMatched = false;
          }
          const re = new RegExp(filter, "g");
          if (item[key] && !re.test(item[key])) {
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
    // This function should appropriately handle a Cell Click given a desired
    // action by the column configuration
    if (column.onClick) {
      if (column.onClick.action === "redirect") {
        this.setState({
          redirect: entry[column.key] + window.location.search || "",
        });
      }
    }
  }

  generateRows() {
    const { expandedRow, filteredData, tableConfig, activePage } = this.state;
    const filteredDataPaginated = filteredData.slice(
      (activePage - 1) * tableConfig.rowsPerPage,
      activePage * tableConfig.rowsPerPage - 1
    );

    if (expandedRow) {
      const { index, data } = expandedRow;
      filteredDataPaginated.splice(index, 0, data);
    }

    return filteredDataPaginated.map((entry, ridx) => {
      // if a row is clicked then show its associated detail row.
      if (expandedRow && expandedRow.index === ridx) {
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

      const cells = [];
      tableConfig.columns.forEach((column, cidx) => {
        if (column.type === "daterange") {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <ReactMarkdown
                source={new Date(entry[column.key] * 1000).toUTCString()}
              />
            </Table.Cell>
          );
        } else if (column.type === "button") {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Button
                content={entry[column.content] || column.content}
                fluid
                labelPosition="right"
                icon={column.icon}
                onClick={(e) => this.handleCellClick(e, column, entry)}
                primary
                size="mini"
              />
            </Table.Cell>
          );
        } else if (column.type === "icon") {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Icon
                onClick={(e) => this.handleCellClick(e, column, entry)}
                link
                name={column.icon}
              />
            </Table.Cell>
          );
        } else if (column.useLabel) {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Label>
                {entry[column.key] != null && entry[column.key].toString()}
              </Label>
            </Table.Cell>
          );
        } else if (column.type === "link") {
          // TODO, provide an option not to send markdown format
          const value =
            entry[column.key] != null && entry[column.key].toString();
          const found = value.match(/\[(.+?)\]\((.+?)\)/);
          if (found) {
            cells.push(
              <Table.Cell
                key={`cell-${ridx}-${cidx}`}
                collapsing
                style={column.style}
              >
                <Link to={found[2]}>{found[1]}</Link>
              </Table.Cell>
            );
          } else {
            cells.push(
              <Table.Cell
                key={`cell-${ridx}-${cidx}`}
                collapsing
                style={column.style}
              >
                <ReactMarkdown
                  source={
                    entry[column.key] != null && entry[column.key].toString()
                  }
                />
              </Table.Cell>
            );
          }
        } else {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <ReactMarkdown
                source={
                  entry[column.key] != null && entry[column.key].toString()
                }
              />
            </Table.Cell>
          );
        }
      });

      return (
        <Table.Row key={`row-${ridx}`}>
          {tableConfig.expandableRows && (
            <Table.Cell key={`expand-cell-${ridx}`} collapsing>
              <Icon
                link
                name={
                  expandedRow && expandedRow.index - 1 === ridx
                    ? "caret down"
                    : "caret right"
                }
                onClick={() => this.handleRowExpansion(ridx)}
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
      warningMessage,
    } = this.state;
    const totalPages = parseInt(
      filteredData.length / tableConfig.rowsPerPage,
      10
    );
    const columns = this.generateColumns();

    if (isLoading) {
      return (
        <Segment basic>
          <Dimmer active inverted size="large">
            <Loader inverted content="Loading" />
          </Dimmer>
        </Segment>
      );
    }

    // TODO (heewonk), revisit following redirection logic when moving to SPA again
    if (redirect) {
      return (
        <BrowserRouter forceRefresh>{this.renderRedirect()}</BrowserRouter>
      );
    }

    return (
      <>
        {warningMessage ? (
          <Message warning>
            <Message.Header>Oops! there was a problem</Message.Header>
            <p>{warningMessage}</p>
          </Message>
        ) : null}
        <Table collapsing sortable celled compact selectable striped>
          {columns}
          <Table.Body>{this.generateRows()}</Table.Body>
          <Table.Footer>
            <Table.Row>
              <Table.HeaderCell collapsing colSpan={this.calculateColumnSize()}>
                {totalPages > 0 ? (
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
                ) : (
                  ""
                )}
              </Table.HeaderCell>
            </Table.Row>
          </Table.Footer>
        </Table>
      </>
    );
  }
}

export default ConsoleMeDataTable;
