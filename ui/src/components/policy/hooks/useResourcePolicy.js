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
    const isManagedPolicy = arn.includes(":policy/");
    const requestV2 = {
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal: {
              principal_arn: arn,
              principal_type: "AwsResource",
            },
            arn,
            change_type: isManagedPolicy
              ? "managed_policy_resource"
              : "resource_policy",
            policy: {
              policy_document:
                state.resourcePolicy.PolicyDocument.PolicyDocument,
            },
            ...(isManagedPolicy && { new: false }),
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
