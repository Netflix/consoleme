import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./inlinePolicyReducer";
import { sendRequestV2 } from "../../../helpers/utils";

const useInlinePolicy = (resource) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    setInlinePolicies(resource.inline_policies);
  }, [resource.inline_policies]);

  const setInlinePolicies = (policies) =>
      dispatch({ type: "SET_POLICIES", policies });
  const setActiveIndex = (activeIndex) =>
      dispatch({ type: "SET_ACTIVE_INDEX", activeIndex });
  const setIsNewPolicy = (isNewPolicy) =>
      dispatch({ type: "SET_IS_NEW_POLICY", isNewPolicy });
  const addInlinePolicy = (policy) => dispatch({ type: "ADD_POLICY", policy });
  const updateInlinePolicy = (policy) => dispatch({ type: "UPDATE_POLICY", policy });
  const deleteInlinePolicy = (policy) => dispatch({ type: "DELETE_POLICY", policy });
  const handleInlinePolicySubmit = async ({ arn, adminAutoApprove, justification }) => {
    const requestV2 = {
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal_arn: arn,
            change_type: "inline_policy",
            new: state.newPolicy.new,
            policy_name: state.newPolicy.PolicyName,
            action: state.newPolicy.action || "attach",
            policy: {
              policy_document: state.newPolicy.PolicyDocument,
            },
          },
        ],
      },
    };
    return sendRequestV2(requestV2);
  };


  return {
    ...state,
    setActiveIndex,
    setIsNewPolicy,
    setInlinePolicies,
    addInlinePolicy,
    updateInlinePolicy,
    deleteInlinePolicy,
    handleInlinePolicySubmit,
  };
};

export default useInlinePolicy;
