import { useReducer } from "react";
import { initialState, reducer } from "./inlinePolicyReducer";
import { sendRequestCommon } from "../../../helpers/utils";

const useInlinePolicy = () => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleInlinePolicySubmit = async (arn) => {
    const { adminAutoApprove, justification, newPolicy, policyType } = state;
    const requestV2 = {
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal_arn: arn,
            change_type: policyType,
            new: newPolicy.new,
            policy_name: newPolicy.PolicyName,
            action: newPolicy.action || "attach",
            policy: {
              policy_document: newPolicy.PolicyDocument,
            },
          },
        ],
      },
    };

    const response = await sendRequestCommon(requestV2, "/api/v2/request");

    if (response) {
      const { request_created, request_id, request_url, errors } = response;
      if (request_created === true) {
        if (adminAutoApprove && errors === 0) {
          return {
            message: `Successfully created and applied request: [${request_id}](${request_url}).`,
            request_created,
            error: false,
          };
        } else if (errors === 0) {
          return {
            message: `Successfully created request: [${request_id}](${request_url}).`,
            request_created,
            error: false,
          };
        } else {
          return {
            message: `This request was created and partially successful: : [${request_id}](${request_url}). But the server reported some errors with the request: ${JSON.stringify(
              response
            )}`,
            request_created,
            error: true,
          };
        }
      }
      return {
        message: `Server reported an error with the request: ${JSON.stringify(
          response
        )}`,
        request_created,
        error: true,
      };
    } else {
      return {
        message: `"Failed to submit request: ${JSON.stringify(response)}`,
        request_created: false,
        error: true,
      };
    }
  };
  const setInlinePolicies = (policies) =>
    dispatch({ type: "SET_POLICIES", policies });
  const setAdminAutoApprove = (approve) =>
    dispatch({ type: "SET_ADMIN_AUTO_APPROVE", approve });
  const setPolicyType = (policyType) =>
    dispatch({ type: "SET_POLICY_TYPE", policyType });
  const setActiveIndex = (activeIndex) =>
    dispatch({ type: "SET_ACTIVE_INDEX", activeIndex });
  const setIsNewPolicy = (isNewPolicy) =>
    dispatch({ type: "SET_IS_NEW_POLICY", isNewPolicy });
  const setTogglePolicyModal = (toggle) =>
    dispatch({ type: "TOGGLE_POLICY_MODAL", toggle });
  const addPolicy = (policy) => dispatch({ type: "ADD_POLICY", policy });
  const updatePolicy = (policy) => dispatch({ type: "UPDATE_POLICY", policy });
  const deletePolicy = (policy) => dispatch({ type: "DELETE_POLICY", policy });
  const setJustification = (justification) =>
    dispatch({ type: "SET_JUSTIFICATION", justification });

  return {
    ...state,
    setActiveIndex,
    setIsNewPolicy,
    setTogglePolicyModal,
    setAdminAutoApprove,
    setInlinePolicies,
    updatePolicy,
    deletePolicy,
    addPolicy,
    setPolicyType,
    setJustification,
    handleInlinePolicySubmit,
  };
};

export default useInlinePolicy;
