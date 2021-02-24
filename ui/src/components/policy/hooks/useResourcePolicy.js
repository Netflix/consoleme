import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./resourcePolicyReducer";
import { usePolicyContext } from "./PolicyProvider";

const useResourcePolicy = () => {
  const { resource = {}, sendRequestV2 } = usePolicyContext();
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    if (!resource.resource_details) {
      return;
    }
    dispatch({
      type: "SET_RESOURCE_POLICY",
      policy: resource.resource_details.Policy,
    });
  }, [resource.resource_details]);

  const handleResourcePolicySubmit = async ({
    arn,
    adminAutoApprove,
    justification,
  }) => {
    const requestV2 = {
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal_arn: arn,
            arn,
            change_type: "resource_policy",
            policy: {
              policy_document:
                state.resourcePolicy.PolicyDocument.PolicyDocument,
            },
          },
        ],
      },
    };
    return sendRequestV2(requestV2);
  };

  return {
    ...state,
    setResourcePolicy: (policy) =>
      dispatch({
        type: "SET_RESOURCE_POLICY",
        policy,
      }),
    handleResourcePolicySubmit,
  };
};

export default useResourcePolicy;
