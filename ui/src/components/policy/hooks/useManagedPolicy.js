import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./managedPolicyReducer";
import { usePolicyContext } from "./PolicyProvider";

const useManagedPolicy = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const {
    params = {},
    resource = {},
    setModalWithAdminAutoApprove,
    sendRequestV2,
  } = usePolicyContext();

  useEffect(() => {
    dispatch({
      type: "SET_MANAGED_POLICIES",
      policies: resource.managed_policies,
    });
  }, [resource.managed_policies]);

  const handleManagedPolicySubmit = async ({
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
            principal: {
              principal_arn: arn,
              principal_type: "AwsResource",
            },
            arn: state.managedPolicyArn,
            change_type: "managed_policy",
            action: state.actionType,
          },
        ],
      },
    };
    return sendRequestV2(requestV2);
  };

  return {
    ...state,
    accountID: params.accountID,
    setModalWithAdminAutoApprove,
    setManagedPolicies: (policies) =>
      dispatch({
        type: "SET_MANAGED_POLICIES",
        policies,
      }),
    resource: resource,
    addManagedPolicy: (arn) => dispatch({ type: "ADD_MANAGED_POLICY", arn }),
    deleteManagedPolicy: (arn) =>
      dispatch({ type: "DELETE_MANAGED_POLICY", arn }),
    handleManagedPolicySubmit,
  };
};

export default useManagedPolicy;
