import { useReducer } from "react";
import { initialState, reducer } from "./inlinePolicyReducer";
import { sendRequestCommon } from "../../../helpers/utils";

const useInlinePolicy = () => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleInlinePolicySubmit = async ({ arn, adminAutoApprove, justification, policyType }) => {
    const { newPolicy } = state;

    let requestV2 = {};
    if (policyType === "inline_policy") {
      requestV2 = {
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
    } else if (policyType === "resource_policy") {
      requestV2 = {
        justification,
        admin_auto_approve: adminAutoApprove,
        changes: {
          changes: [
            {
              principal_arn: arn,
              arn: arn,
              change_type: policyType,
              policy: {
                policy_document: newPolicy.PolicyDocument,
              },
            },
          ],
        },
      };
    }

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
  const setResourcePolicy = (policy) =>
    dispatch({ type: "SET_RESOURCE_POLICY", policy });
  const setInlinePolicies = (policies) =>
    dispatch({ type: "SET_POLICIES", policies });
  const setActiveIndex = (activeIndex) =>
    dispatch({ type: "SET_ACTIVE_INDEX", activeIndex });
  const setIsNewPolicy = (isNewPolicy) =>
    dispatch({ type: "SET_IS_NEW_POLICY", isNewPolicy });
  const addPolicy = (policy) => dispatch({ type: "ADD_POLICY", policy });
  const updatePolicy = (policy) => dispatch({ type: "UPDATE_POLICY", policy });
  const deletePolicy = (policy) => dispatch({ type: "DELETE_POLICY", policy });

  return {
    ...state,
    setActiveIndex,
    setIsNewPolicy,
    setInlinePolicies,
    setResourcePolicy,
    updatePolicy,
    deletePolicy,
    addPolicy,
    handleInlinePolicySubmit,
  };
};

export default useInlinePolicy;
