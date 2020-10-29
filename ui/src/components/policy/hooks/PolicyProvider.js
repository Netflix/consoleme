import React, { useContext, useEffect, useReducer } from "react";
import { initialState, reducer } from "./policyReducer";
import { useParams } from "react-router-dom";
import { sendRequestCommon } from "../../../helpers/utils";
import useInlinePolicy from "./useInlinePolicy";

const PolicyContext = React.createContext(initialState);

export const usePolicyContext = () => useContext(PolicyContext);

export const PolicyProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { accountID, serviceType, region, resourceName } = useParams();

  // Resource fetching happens only when location is changed and when a policy is added/updated/removed.
  useEffect(() => {
    (async () => {
      const location = ((accountID, serviceType, region, resourceName) => {
        switch (serviceType) {
          case "iamrole": {
            return `/api/v2/roles/${accountID}/${resourceName}`;
          }
          case "s3": {
            return `/api/v2/resources/${accountID}/s3/${resourceName}`;
          }
          case "sqs": {
            return `/api/v2/resources/${accountID}/sqs/${region}/${resourceName}`;
          }
          case "sns": {
            return `/api/v2/resources/${accountID}/sns/${region}/${resourceName}`;
          }
          default: {
            throw new Error("No such service exist");
          }
        }
      })(accountID, serviceType, region, resourceName);
      setIsPolicyEditorLoading(true);
      const resource = await sendRequestCommon(null, location, "get");
      setParams({ accountID, region, resourceName, serviceType });
      setResource(resource);
      if (serviceType === "iamrole") {
        inlinePolicyHooks.setInlinePolicies(resource.inline_policies);
      } else if (resource && resource.resource_details) {
        inlinePolicyHooks.setResourcePolicy(resource.resource_details.Policy);
      }
      setTags(resource.tags);
      setIsPolicyEditorLoading(false);
    })();
  }, [accountID, region, resourceName, serviceType, state.isSuccess]); //eslint-disable-line

  // PolicyEditor States Handlers
  const setParams = (params) => dispatch({ type: "UPDATE_PARAMS", params });
  const setResource = (resource) =>
    dispatch({ type: "UPDATE_RESOURCE", resource });
  const setIsPolicyEditorLoading = (loading) =>
    dispatch({ type: "TOGGLE_LOADING", loading });
  const setToggleDeleteRole = (toggle) =>
    dispatch({ type: "TOGGLE_DELETE_ROLE", toggle });
  const setIsSuccess = (isSuccess) =>
    dispatch({ type: "SET_IS_SUCCESS", isSuccess });
  const setTags = (tags) => dispatch({ type: "SET_TAGS", tags });
  const createTag = (tag) => dispatch({ type: "CREATE_TAG", tag });
  const deleteTag = (key) => dispatch({ type: "DELETE_TAG", key });
  const updateTag = (tag) => dispatch({ type: "UPDATE_TAG", tag });
  const toggleNewTag = (toggle) => dispatch({ type: "TOGGLE_NEW_TAG", toggle });
  const handleTagSave = () => {
    // TODO, add a logic to save tags
    console.log(state.tagChanges);
  };
  // InlinePolicy States Handler
  const inlinePolicyHooks = useInlinePolicy();

  // There are chances that same state and handler exists in other hooks
  return (
    <PolicyContext.Provider
      value={{
        ...state,
        setResource,
        setIsPolicyEditorLoading,
        setToggleDeleteRole,
        setIsSuccess,
        setTags,
        createTag,
        deleteTag,
        updateTag,
        toggleNewTag,
        handleTagSave,
        ...inlinePolicyHooks,
      }}
    >
      {children}
    </PolicyContext.Provider>
  );
};
