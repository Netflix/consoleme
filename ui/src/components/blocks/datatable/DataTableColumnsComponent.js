import React from "react";
import { Dropdown, Header, Input, Label, Table } from "semantic-ui-react";
import SemanticDatepicker from "react-semantic-ui-datepickers";
import _ from "lodash";

const DataTableColumnsComponent = ({
  column,
  data,
  totalCount,
  filteredCount,
  direction,
  filters,
  filterColumn,
  filterDateRangeTime,
  filteredData,
  setFilteredData,
  tableConfig,
}) => {
  const generateColumnOptions = (data) => {
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
          text: item,
        });
      });
    }

    return columnOptions;
  };

  const handleSort = (clickedColumn, column, filteredData, direction) => {
    // Things that happening in this sorting event handler are following:
    // - Sort the filteredData list by the name of column a user clicked.
    // - Keep track of which column was clicked for sorting.
    // - Keep track of sorting order last time it was used.
    let sortedData = {
      totalCount: totalCount,
      filteredCount: filteredCount,
    };
    if (column !== clickedColumn) {
      sortedData.data = _.sortBy(filteredData, [clickedColumn]);
      setFilteredData(sortedData, "ascending", clickedColumn);
    } else {
      sortedData.data = filteredData.reverse();
      setFilteredData(
        sortedData,
        direction === "ascending" ? "descending" : "ascending",
        clickedColumn
      );
    }
  };

  const columns = [];
  const columnOptions = generateColumnOptions(data);

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
            onChange={filterColumn}
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
            onChange={filterColumn}
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
            onChange={filterColumn}
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
          <div
            onClick={(e) => {
              e.stopPropagation();
            }}
            style={{
              display: "inline",
            }}
          >
            <SemanticDatepicker
              name={item.key}
              style={item.style}
              onChange={filterDateRangeTime}
              type="range"
              compact
            />
          </div>
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
        onClick={() => {
          handleSort(key, column, filteredData, direction);
        }}
        sorted={
          column === item.key && !["button"].includes(item.type)
            ? direction
            : null
        }
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

export default DataTableColumnsComponent;
