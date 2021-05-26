import { useCallback, useEffect, useReducer } from "react";
import { usePolicyContext } from "./PolicyProvider";
import { initialState, reducer } from "./inlinePolicyReducer";

const useInlinePolicy = () => {
  const { resource = {}, sendRequestV2 } = usePolicyContext();
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    dispatch({ type: "SET_POLICIES", policies: resource.inline_policies });
  }, [resource.inline_policies]);

  const handleInlinePolicySubmit = async ({
    arn,
    adminAutoApprove,
    justification,
  }) => {
    return sendRequestV2({
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal: {
              principal_arn: arn,
              principal_type: "AwsResource",
            },
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
    });
  };

  return {
    ...state,
    arn: resource?.arn,
    setInlinePolicies: (policies) =>
      dispatch({ type: "SET_POLICIES", policies }),
    setIsNewPolicy: useCallback(
      (isNewPolicy) => dispatch({ type: "SET_IS_NEW_POLICY", isNewPolicy }),
      []
    ),
    addInlinePolicy: useCallback(
      (policy) => dispatch({ type: "ADD_POLICY", policy }),
      []
    ),
    updateInlinePolicy: useCallback(
      (policy) => dispatch({ type: "UPDATE_POLICY", policy }),
      []
    ),
    deleteInlinePolicy: useCallback(
      (policy) => dispatch({ type: "DELETE_POLICY", policy }),
      []
    ),
    handleInlinePolicySubmit,
  };
};

export default useInlinePolicy;
