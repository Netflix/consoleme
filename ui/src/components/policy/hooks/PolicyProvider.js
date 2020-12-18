import React, { useContext, useEffect, useReducer } from "react";
import { useParams } from "react-router-dom";
import { initialState, reducer } from "./policyReducer";
import { getResourceEndpoint, sendRequestCommon } from "../../../helpers/utils";

const PolicyContext = React.createContext(initialState);

export const usePolicyContext = () => useContext(PolicyContext);

export const PolicyProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { accountID, serviceType, region, resourceName } = useParams();

  // PolicyEditor States Handlers
  const setParams = (params) => dispatch({ type: "UPDATE_PARAMS", params });
  const setResource = (resource) =>
    dispatch({ type: "UPDATE_RESOURCE", resource });
  const setIsPolicyEditorLoading = (loading) =>
    dispatch({ type: "TOGGLE_LOADING", loading });
  const setToggleDeleteRole = (toggle) =>
    dispatch({ type: "TOGGLE_DELETE_ROLE", toggle });
  const setToggleRefreshRole = (toggle) =>
    dispatch({ type: "TOGGLE_REFRESH_ROLE", toggle });
  const setIsSuccess = (isSuccess) =>
    dispatch({ type: "SET_IS_SUCCESS", isSuccess });

  // Resource fetching happens only when location is changed and when a policy is added/updated/removed.
  useEffect(() => {
    (async () => {
      // store resource metadata from the url
      setParams({ accountID, region, resourceName, serviceType });
      // get the endpoint by corresponding service type e.g. s3, iamrole, sqs
      const endpoint = getResourceEndpoint(
        accountID,
        serviceType,
        region,
        resourceName
      );
      // set loader to start fetching resource from the backend.
      setIsPolicyEditorLoading(true);
      // retrieve resource from the endpoint and set resource state
      const resource = await sendRequestCommon(
        null,
        endpoint,
        "get"
      );
      setResource(resource);
      setIsPolicyEditorLoading(false);
    })();
  }, [
    accountID,
    region,
    resourceName,
    serviceType,
    state.isSuccess,
  ]); //eslint-disable-line

  useEffect(() => {
    (async () => {
      const endpoint = getResourceEndpoint(
        accountID,
        serviceType,
        region,
        resourceName
      );
      if (!state.toggleRefreshRole) {
        return;
      }
      setIsPolicyEditorLoading(true);
      const resource = await sendRequestCommon(
        null,
        `${endpoint}?force_refresh=true`,
        "get"
      );
      setResource(resource);
      setIsPolicyEditorLoading(false);
      setToggleRefreshRole(false);
    })()
  }, [state.toggleRefreshRole]);  //eslint-disable-line

  // Mostly used for Justification Modal
  const setModalWithAdminAutoApprove = (approve) =>
    dispatch({ type: "SET_ADMIN_AUTO_APPROVE", approve });
  const setTogglePolicyModal = (toggle) =>
    dispatch({ type: "TOGGLE_POLICY_MODAL", toggle });

  const handleDeleteRole = async () => {
    const { accountID, resourceName } = state.params;
    return await sendRequestCommon(
      null,
      `/api/v2/roles/${accountID}/${resourceName}`,
      "delete"
    );
  };

  // There are chances that same state and handler exists in other hooks
  return (
    <PolicyContext.Provider
      value={{
        ...state,
        setResource,
        setIsPolicyEditorLoading,
        setToggleDeleteRole,
        setToggleRefreshRole,
        setIsSuccess,
        setTogglePolicyModal,
        setModalWithAdminAutoApprove,
        handleDeleteRole,
      }}
    >
      {children}
    </PolicyContext.Provider>
  );
};
