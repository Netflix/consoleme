import React, { useContext, useEffect, useReducer } from "react";
import { initialState, reducer } from "./policyReducer";
import { useParams } from "react-router-dom";
import { getResourceEndpoint, sendRequestCommon } from "../../../helpers/utils";

const PolicyContext = React.createContext(initialState);

export const usePolicyContext = () => useContext(PolicyContext);

export const PolicyProvider = ({ children }) => {
    const [state, dispatch] = useReducer(reducer, initialState);
    const { accountID, serviceType, region, resourceName } = useParams();

    // Resource fetching happens only when location is changed and when a policy is added/updated/removed.
    useEffect(() => {
        (async () => {
            // store resource metadata from the url
            setParams({ accountID, region, resourceName, serviceType });

            // get the endpoint by corresponding service type e.g. s3, iamrole, sqs
            const endpoint = getResourceEndpoint(accountID, serviceType, region, resourceName);

            // set loader to start fetching resource from the backend.
            setIsPolicyEditorLoading(true);

            // retrive resource from the endpoint and set resource state
            const resource = await sendRequestCommon(null, endpoint, "get");
            setResource(resource);

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

    // Mostly used for Justification Modal
    const setAdminAutoApprove = (approve) =>
        dispatch({ type: "SET_ADMIN_AUTO_APPROVE", approve });
    const setContext = (context) =>
        dispatch({ type: "SET_CONTEXT", context });
    const setTogglePolicyModal = (toggle) =>
        dispatch({ type: "TOGGLE_POLICY_MODAL", toggle });

    // There are chances that same state and handler exists in other hooks
    return (
        <PolicyContext.Provider
            value={{
                ...state,
                setResource,
                setIsPolicyEditorLoading,
                setToggleDeleteRole,
                setIsSuccess,
                setContext,
                setTogglePolicyModal,
                setAdminAutoApprove,
            }}
        >
            {children}
        </PolicyContext.Provider>
    );
};
