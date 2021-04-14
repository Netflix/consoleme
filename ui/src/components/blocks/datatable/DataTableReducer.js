export const initialState = {
  activePage: 1,
  column: null,
  data: [],
  debounceWait: 500,
  direction: "descending",
  expandedRow: null,
  filteredData: [],
  filters: {},
  isLoading: true,
  redirect: false,
  tableConfig: {
    columns: [],
    dataEndpoint: "",
    expandableRows: true,
    rowsPerPage: 50,
    serverSideFiltering: true,
    sortable: true,
    tableName: "",
    tableDescription: "",
    totalRows: 1000,
  },
  warningMessage: "",
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_TABLE_CONFIG": {
      return {
        ...state,
        tableConfig: action.tableConfig,
      };
    }
    case "SET_DATA": {
      return {
        ...state,
        data: action.data.data,
        filteredData: action.data.data,
        totalCount: action.data.totalCount,
        filteredCount: action.data.filteredCount,
        isLoading: false,
      };
    }
    case "SET_FILTERS": {
      return {
        ...state,
        filters: action.filters,
      };
    }
    case "SET_WARNINGS": {
      return {
        ...state,
        warningMessage: action.warningMessage,
      };
    }
    case "SET_FILTERED_DATA": {
      return {
        ...state,
        expandedRow: null,
        filteredData: action.filteredData.data || [],
        filteredCount: action.filteredData.filteredCount,
        totalCount: action.filteredData.totalCount,
        activePage: 1,
        direction: action.direction || "descending",
        column: action.clickedColumn || null,
        isLoading: false,
      };
    }
    case "SET_REDIRECT": {
      return {
        ...state,
        redirect: action.redirect,
      };
    }
    case "SET_EXPANDED_ROW": {
      return {
        ...state,
        expandedRow: action.expandedRow,
      };
    }
    case "SET_ACTIVE_PAGE": {
      return {
        ...state,
        activePage: action.activePage,
        expandedRow: null,
      };
    }
    default: {
      return state;
    }
  }
};
