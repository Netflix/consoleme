import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./assumeRolePolicyReducer";
import { usePolicyContext } from "./PolicyProvider";

const useAssumeRolePolicy = () => {
  const { resource, sendRequestV2 } = usePolicyContext();
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    dispatch({
      type: "SET_ASSUMEROLE_POLICY",
      policy: resource.assume_role_policy_document,
    });
  }, [resource.assume_role_policy_document]);

  const handleAssumeRolePolicySubmit = async ({
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
            change_type: "assume_role_policy",
            policy_name: state.assumeRolePolicy.PolicyName,
            policy: {
              policy_document:
                state.assumeRolePolicy.PolicyDocument.PolicyDocument,
            },
          },
        ],
      },
    });
  };

  return {
    ...state,
    setAssumeRolePolicy: (policy) =>
      dispatch({ type: "SET_ASSUMEROLE_POLICY", policy }),
    handleAssumeRolePolicySubmit,
  };
};

export default useAssumeRolePolicy;
