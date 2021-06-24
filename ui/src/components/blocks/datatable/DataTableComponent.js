import React from "react";
import { Redirect, BrowserRouter } from "react-router-dom";
import useDataTable from "./useDataTable";
import {
  Dimmer,
  Loader,
  Message,
  Pagination,
  Segment,
  Table,
} from "semantic-ui-react";
import DataTableActionsComponent from "./DataTableActionsComponent";
import DataTableColumnsComponent from "./DataTableColumnsComponent";
import DataTableRowsComponent from "./DataTableRowsComponent";

import "react-semantic-ui-datepickers/dist/react-semantic-ui-datepickers.css";

const DEFAULT_ROWS_PER_PAGE = 50;

const DataTableComponent = ({ config }) => {
  const {
    activePage = 1,
    column = null,
    data = [],
    direction = "descending",
    expandedRow = null,
    filteredData = [],
    filters = {},
    totalCount = 0,
    filteredCount = 0,
    isLoading = true,
    redirect = false,
    tableConfig = {},
    warningMessage = "",
    filterColumn,
    filterDateRangeTime,
    setActivePage,
    setExpandedRow,
    setFilteredData,
    setRedirect,
  } = useDataTable(config);

  const calculateColumnSize = (tableConfig) => {
    return (
      (tableConfig.columns || []).length + (tableConfig.expandableRows ? 1 : 0)
    );
  };

  const rowsPerPage = tableConfig.rowsPerPage || DEFAULT_ROWS_PER_PAGE;
  const totalPages = parseInt(filteredData.length / rowsPerPage, 10);

  if (isLoading) {
    return (
      <Segment basic>
        <Dimmer active inverted size="large">
          <Loader inverted content="Loading" />
        </Dimmer>
      </Segment>
    );
  }

  // TODO, if redirection is happening within ConsoleMe namespace then use useHistory
  if (redirect) {
    return (
      <BrowserRouter forceRefresh>
        <Redirect to={redirect} />
      </BrowserRouter>
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

      <DataTableActionsComponent filters={filters} tableConfig={tableConfig} />

      <Table sortable celled compact selectable striped>
        <DataTableColumnsComponent
          column={column}
          data={data}
          totalCount={totalCount}
          filteredCount={filteredCount}
          direction={direction}
          filters={filters}
          filterColumn={filterColumn}
          filterDateRangeTime={filterDateRangeTime}
          filteredData={filteredData}
          setFilteredData={setFilteredData}
          tableConfig={tableConfig}
        />
        <Table.Body>
          <DataTableRowsComponent
            activePage={activePage}
            expandedRow={expandedRow}
            filteredData={filteredData}
            tableConfig={tableConfig}
            calculateColumnSize={calculateColumnSize}
            setExpandedRow={setExpandedRow}
            setRedirect={setRedirect}
          />
        </Table.Body>
        <Table.Footer>
          <Table.Row>
            <Table.HeaderCell colSpan={calculateColumnSize(tableConfig)}>
              <div
                style={{
                  alignItems: "center",
                  display: "flex",
                  justifyContent: "space-between",
                  marginRight: "1em",
                }}
              >
                <div>
                  {filteredCount !== totalCount ? (
                    <>
                      {filteredCount.toLocaleString()} Results (Filtered from{" "}
                      {totalCount.toLocaleString()})
                    </>
                  ) : (
                    <>{filteredCount.toLocaleString()} Results</>
                  )}
                </div>
                {totalPages > 0 ? (
                  <Pagination
                    activePage={activePage}
                    totalPages={totalPages}
                    onPageChange={(event, data) => {
                      setActivePage(data.activePage);
                    }}
                  />
                ) : (
                  ""
                )}
              </div>
            </Table.HeaderCell>
          </Table.Row>
        </Table.Footer>
      </Table>
    </>
  );
};

export default DataTableComponent;
