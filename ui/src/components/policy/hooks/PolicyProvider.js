import React, { useContext, useEffect, useReducer } from "react";
import { initialState, reducer } from "./policyReducer";
import { useParams } from "react-router-dom";
import { sendRequestCommon } from "../../../helpers/utils";
import useInlinePolicy from "./useInlinePolicy";
import usePolicyTag from "./usePolicyTag";

const PolicyContext = React.createContext(initialState);

export const usePolicyContext = () => useContext(PolicyContext);

export const PolicyProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { accountID, serviceType, region, resourceName } = useParams();

  // InlinePolicy States Handler
  const inlinePolicyHooks = useInlinePolicy();
  const policyTagHooks = usePolicyTag();

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
        policyTagHooks.setTags(resource.tags);
        inlinePolicyHooks.setInlinePolicies(resource.inline_policies);
        setPolicyType("inline_policy");
      } else if (resource && resource.resource_details) {
        policyTagHooks.setTags(resource.resource_details.TagSet);
        inlinePolicyHooks.setResourcePolicy(resource.resource_details.Policy);
        setPolicyType("resource_policy");
      }
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

  const setAdminAutoApprove = (approve) =>
    dispatch({ type: "SET_ADMIN_AUTO_APPROVE", approve });
  const setPolicyType = (policyType) =>
    dispatch({ type: "SET_POLICY_TYPE", policyType });
  const setTogglePolicyModal = (toggle) =>
    dispatch({ type: "TOGGLE_POLICY_MODAL", toggle });
  const setJustification = (justification) =>
    dispatch({ type: "SET_JUSTIFICATION", justification });

  // There are chances that same state and handler exists in other hooks
  return (
    <PolicyContext.Provider
      value={{
        ...state,
        setResource,
        setIsPolicyEditorLoading,
        setToggleDeleteRole,
        setIsSuccess,
        setPolicyType,
        setJustification,
        setTogglePolicyModal,
        setAdminAutoApprove,
        ...inlinePolicyHooks,
        ...policyTagHooks,
      }}
    >
      {children}
    </PolicyContext.Provider>
  );
};
