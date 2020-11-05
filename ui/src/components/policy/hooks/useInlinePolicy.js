import { useEffect, useReducer } from "react";
import { usePolicyContext } from "./PolicyProvider";
import { initialState, reducer } from "./inlinePolicyReducer";
import { sendRequestV2 } from "../../../helpers/utils";

const useInlinePolicy = () => {
  const { resource = {} } = usePolicyContext();
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    dispatch({ type: "SET_POLICIES", policies: resource.inline_policies })
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
    });
  };

  return {
    ...state,
    arn: resource?.arn,
    setActiveIndex: (activeIndex) =>
      dispatch({ type: "SET_ACTIVE_INDEX", activeIndex }),
    setIsNewPolicy: (isNewPolicy) =>
      dispatch({ type: "SET_IS_NEW_POLICY", isNewPolicy }),
    setInlinePolicies: (policies) =>
      dispatch({ type: "SET_POLICIES", policies }),
    addInlinePolicy: (policy) =>
      dispatch({ type: "ADD_POLICY", policy }),
    updateInlinePolicy: (policy) =>
      dispatch({ type: "UPDATE_POLICY", policy }),
    deleteInlinePolicy: (policy) =>
      dispatch({ type: "DELETE_POLICY", policy }),
    handleInlinePolicySubmit,
  };
};

export default useInlinePolicy;
