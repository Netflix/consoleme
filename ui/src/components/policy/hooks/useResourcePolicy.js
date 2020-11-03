import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./resourcePolicyReducer";
import { sendRequestV2 } from "../../../helpers/utils";

const useResourcePolicy = (resource) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  useEffect(() => {
    if (!resource.resource_details) {
      return;
    }
    setResourcePolicy(resource.resource_details.Policy);
  }, [resource.resource_details]);

  const setResourcePolicy = (policy) =>
    dispatch({ type: "SET_RESOURCE_POLICY", policy });

  const handleResourcePolicySubmit = async ({
    arn,
    adminAutoApprove,
    context,
    justification,
  }) => {
    const requestV2 = {
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: [
          {
            principal_arn: arn,
            arn: arn,
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
    setResourcePolicy,
    handleResourcePolicySubmit,
  };
};

export default useResourcePolicy;
