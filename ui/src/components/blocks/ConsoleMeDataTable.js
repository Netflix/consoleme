import _ from "lodash";
import qs from "qs";
import React, { useState, useEffect } from "react";
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
import { sendRequestCommon } from "../../helpers/utils";

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

const ConsoleMeDataTable = (props) => {
  const { config } = props;
  const initialStateN = {
    ...initialState,
    tableConfig: config,
  };
  const [state, setState] = useState(initialStateN);

  let timer = null;

  useEffect(async () => {
    if (state.isLoading) {
      let data = await sendRequestCommon(
        {
          limit: tableConfig.totalRows,
        },
        tableConfig.dataEndpoint
      );

      // This means it raised an exception from fetching data
      if (data.status) {
        data = [];
      }

      setState({
        ...state,
        data,
        filteredData: data,
        isLoading: false,
      });
    } else {
      const cb = async () => {
        await generateFilterFromQueryString();
        await generateMessagesFromQueryString();
      };
      cb();
    }
  }, [state.isLoading]);

  useEffect(() => {
    const { tableConfig } = state;
    setState({
      ...state,
      isLoading: true,
    });
  }, []);

  const calculateColumnSize = () => {
    const { tableConfig } = state;
    return (
      (tableConfig.columns || []).length + (tableConfig.expandableRows ? 1 : 0)
    );
  };

  const handleSort = (clickedColumn) => {
    const { column, filteredData, direction } = state;

    if (column !== clickedColumn) {
      return setState({
        ...state,
        column: clickedColumn,
        filteredData: _.sortBy(filteredData, [clickedColumn]),
        direction: "ascending",
      });
    }

    setState({
      ...state,
      filteredData: filteredData.reverse(),
      direction: direction === "ascending" ? "descending" : "ascending",
    });
    return true;
  };

  const handleRowExpansion = (idx) => {
    const { expandedRow, filteredData, tableConfig, activePage } = state;

    // close expansion if there is any expanded row.
    if (expandedRow && expandedRow.index === idx + 1) {
      setState({
        ...state,
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
      setState({
        ...state,
        expandedRow: newExpandedRow,
      });
    }
    return true;
  };

  const generateColumnOptions = () => {
    const { data = [] } = state;
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
  };

  const generateColumns = () => {
    const { direction, tableConfig, filters } = state;
    const columnOptions = generateColumnOptions();
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
              onChange={(e) => filterColumn(e, e.target)}
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
              onChange={(e) => filterColumn(e, e.target)}
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
              onChange={(e) => filterColumn(e, e.target)}
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
              onChange={(e) => filterDateRangeTime(e, e.target)}
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
          onClick={() => handleSort(key)}
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
  };

  const generateMessagesFromQueryString = async () => {
    const parsedQueryString = qs.parse(window.location.search, {
      ignoreQueryPrefix: true,
    });
    if (parsedQueryString) {
      Object.keys(parsedQueryString).forEach((key) => {
        if (key === "warningMessage") {
          setState({
            ...state,
            warningMessage: atob(parsedQueryString[key]),
          });
        }
      });
    }
  };

  const generateFilterFromQueryString = async () => {
    const { tableConfig } = state;
    const parsedQueryString = qs.parse(window.location.search, {
      ignoreQueryPrefix: true,
    });
    const filters = {};
    if (parsedQueryString) {
      Object.keys(parsedQueryString).forEach((key) => {
        filters[key] = parsedQueryString[key];
      });
    }

    setState({
      ...state,
      filters,
    });

    if (tableConfig.serverSideFiltering) {
      await filterColumnServerSide({}, filters);
    } else {
      filterColumnClientSide({}, filters);
    }
  };

  const filterDateRangeTime = async (event, data) => {
    // Convert epoch milliseconds to epoch seconds
    if (data.value && data.value[0] && data.value[1]) {
      const startTime = parseInt(data.value[0].getTime() / 1000, 10);
      const endTime = parseInt(data.value[1].getTime() / 1000, 10);
      await filterColumn(_, {
        name: data.name,
        value: [startTime, endTime],
      });
    }
  };

  const filterColumn = async (event, data) => {
    setState({ ...state, loading: true });
    const { name, value } = data;
    const { tableConfig } = state;

    const { filters } = state;
    filters[name] = value;
    setState({
      ...state,
      filters,
    });

    if (tableConfig.serverSideFiltering) {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        await filterColumnServerSide({}, filters);
      }, state.debounceWait);
    } else {
      clearTimeout(timer);
      timer = setTimeout(() => {
        filterColumnClientSide(event, filters);
      }, state.debounceWait);
    }
  };

  const filterColumnServerSide = async (event, filters) => {
    const { tableConfig } = state;
    let filteredData = await sendRequestCommon(
      { filters },
      tableConfig.dataEndpoint
    );
    if (filteredData.status) {
      filteredData = [];
    }
    setState({
      ...state,
      expandedRow: null,
      filteredData,
      loading: false,
      activePage: 1,
    });
  };

  const filterColumnClientSide = (event, filters) => {
    const { data } = state;
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

    setState({
      ...state,
      expandedRow: null,
      filteredData: filtered,
      loading: false,
      activePage: 1,
    });
  };

  const handleCellClick = (e, column, entry) => {
    // This function should appropriately handle a Cell Click given a desired
    // action by the column configuration
    if (column.onClick) {
      if (column.onClick.action === "redirect") {
        setState({
          ...state,
          redirect: entry[column.key] + window.location.search || "",
        });
      }
    }
  };

  const generateRows = () => {
    const { expandedRow, filteredData, tableConfig, activePage } = state;
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
            <Table.Cell collapsing colSpan={calculateColumnSize()}>
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
                onClick={(e) => handleCellClick(e, column, entry)}
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
                onClick={(e) => handleCellClick(e, column, entry)}
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
                onClick={() => handleRowExpansion(ridx)}
              />
            </Table.Cell>
          )}
          {cells}
        </Table.Row>
      );
    });
  };

  const renderRedirect = () => {
    const { redirect } = state;
    if (redirect) {
      return <Redirect to={redirect} />;
    }
    return true;
  };

  const {
    activePage,
    filteredData,
    isLoading,
    redirect,
    tableConfig,
    warningMessage,
  } = state;
  const totalPages = parseInt(
    filteredData.length / tableConfig.rowsPerPage,
    10
  );
  const columns = generateColumns();

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
    return <BrowserRouter forceRefresh>{renderRedirect()}</BrowserRouter>;
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
        <Table.Body>{generateRows()}</Table.Body>
        <Table.Footer>
          <Table.Row>
            <Table.HeaderCell collapsing colSpan={calculateColumnSize()}>
              {totalPages > 0 ? (
                <Pagination
                  floated="right"
                  defaultActivePage={activePage}
                  totalPages={totalPages}
                  onPageChange={(event, data) => {
                    setState({
                      ...state,
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
};

export default ConsoleMeDataTable;
