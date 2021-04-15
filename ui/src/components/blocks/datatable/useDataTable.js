import { useCallback, useEffect, useReducer, useRef } from "react";
import { initialState, reducer } from "./DataTableReducer";
import { useAuth } from "../../../auth/AuthProviderDefault";
import _ from "lodash";
import qs from "qs";

const useDataTable = (config) => {
  const { sendRequestCommon } = useAuth();
  const [state, dispatch] = useReducer(reducer, initialState);
  const { data, totalCount, debounceWait, filters, tableConfig } = state;

  const setFilteredData = (filteredData, direction, clickedColumn) =>
    dispatch({
      type: "SET_FILTERED_DATA",
      filteredData,
      direction,
      clickedColumn,
    });

  const timeoutRef = useRef();

  const filterColumn = async (_, data) => {
    const { name, value } = data;
    filters[name] = value;
    dispatch({
      type: "SET_FILTERS",
      filters,
    });
    if (tableConfig.serverSideFiltering) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(async () => {
        await filterColumnServerSide(filters);
      }, debounceWait);
    } else {
      clearTimeout(timeoutRef);
      timeoutRef.current = setTimeout(() => {
        filterColumnClientSide(filters);
      }, debounceWait);
    }
  };

  const filterColumnServerSide = useCallback(
    async (filters) => {
      let filteredData = await sendRequestCommon(
        { filters },
        tableConfig.dataEndpoint
      );
      if (!filteredData) {
        return;
      }
      if (filteredData.status) {
        filteredData = [];
      }
      setFilteredData(filteredData);
    },
    [sendRequestCommon, tableConfig]
  );

  const filterColumnClientSide = useCallback(
    (filters) => {
      let filteredData = {};
      if (Object.keys(filters).length > 0) {
        filteredData.data = data.filter((item) => {
          let isMatched = true;
          Object.keys(filters).forEach((key) => {
            const filter = filters[key];
            const re = new RegExp(filter, "g");
            if (item[key] && !re.test(item[key])) {
              isMatched = false;
            }
          });
          return isMatched;
        });
      } else {
        filteredData.data = data;
      }
      filteredData.totalCount = totalCount || 0;
      filteredData.filteredCount = filteredData?.data?.length || 0;
      setFilteredData(filteredData);
    },
    [data, totalCount]
  );

  const filterDateRangeTime = async (event, data) => {
    // Convert epoch milliseconds to epoch seconds
    if (data.value) {
      let startTime = 0;
      let endTime = Number.MAX_SAFE_INTEGER;
      if (data.value.length > 0) {
        startTime = parseInt(data.value[0].getTime() / 1000, 10);
      }
      if (data.value.length > 1) {
        endTime = parseInt(data.value[1].getTime() / 1000, 10);
      }
      await filterColumn(_, {
        name: data.name,
        value: [startTime, endTime],
      });
    } else {
      await filterColumn(_, {
        name: data.name,
        value: [],
      });
    }
  };

  useEffect(() => {
    return () => {
      clearTimeout(timeoutRef.current);
    };
  }, []);

  useEffect(() => {
    dispatch({
      type: "SET_TABLE_CONFIG",
      tableConfig: config,
    });
  }, [config]);

  // TODO, Try consolidate this data fetching useEffect with the server/client side filtering useEffect.
  // This useEffect handles the initial data fetching from the backend to set data state
  useEffect(() => {
    (async (tableConfig) => {
      const {
        dataEndpoint = "",
        serverSideFiltering = true,
        totalRows = 1000,
      } = tableConfig;

      // This means the tableConfig is not loaded and where to fetch the backend data is unknown
      if (_.isEmpty(dataEndpoint)) {
        return;
      }

      // If query string exist and this is a server side filtering then let the filter useEffect
      // fetch the filtered data instead of fetching data from this useEffect.
      if (!_.isEmpty(window.location.search) && serverSideFiltering) {
        return;
      }

      let data = await sendRequestCommon({ limit: totalRows }, dataEndpoint);

      // This means it raised an exception from fetching data
      if (data && data.status != null) {
        data = [];
      }

      dispatch({
        type: "SET_DATA",
        data: data || [],
      });
    })(tableConfig);
  }, [tableConfig, sendRequestCommon]);

  // This useEffect handles the filtering from the url search query. Depends on how the table
  // is configured, it will either apply the filter from the backend or do the filtering from client side.
  useEffect(() => {
    (async (data, tableConfig) => {
      const { dataEndpoint = "", serverSideFiltering = true } = tableConfig;
      // Only skip when the data is empty and filtering is done at the client side.
      if (_.isEmpty(data) && !serverSideFiltering) {
        return;
      }
      // Skip when tableConfig is not fully loaded.
      if (_.isEmpty(dataEndpoint)) {
        return;
      }
      const filters = {};
      const parsedQueryString = qs.parse(window.location.search, {
        ignoreQueryPrefix: true,
      });
      if (parsedQueryString) {
        Object.keys(parsedQueryString).forEach((key) => {
          if (key === "warningMessage") {
            dispatch({
              type: "SET_WARNINGS",
              warningMessage: atob(parsedQueryString[key]),
            });
          } else {
            filters[key] = parsedQueryString[key];
          }
        });
      }
      dispatch({
        type: "SET_FILTERS",
        filters,
      });

      // Filtering is done at the backend and the filtered data is assigned to the state.
      if (serverSideFiltering && Object.keys(filters).length > 0) {
        await filterColumnServerSide(filters);
      } else {
        // This is the client side filtering on the already loaded data.
        filterColumnClientSide(filters);
      }
    })(data, tableConfig);
  }, [data, tableConfig, filterColumnServerSide, filterColumnClientSide]);

  const setActivePage = (activePage) =>
    dispatch({ type: "SET_ACTIVE_PAGE", activePage });
  const setExpandedRow = (expandedRow) =>
    dispatch({ type: "SET_EXPANDED_ROW", expandedRow });
  const setRedirect = (redirect) =>
    dispatch({ type: "SET_REDIRECT", redirect });

  return {
    ...state,
    filterColumn,
    filterDateRangeTime,
    setActivePage,
    setExpandedRow,
    setFilteredData,
    setRedirect,
  };
};

export default useDataTable;
