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
    dispatch({
      type: "SET_PERMISSION_BOUNDARY",
      permission_boundary: resource?.permission_boundary,
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
            principal_arn: arn,
            arn: state.managedPolicyArn,
            change_type: "managed_policy",
            action: state.actionType,
          },
        ],
      },
    };
    return sendRequestV2(requestV2);
  };

  const handlePermissionBoundarySubmit = async ({
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
            arn: state.managedPolicyArn,
            change_type: "permission_boundary",
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
    addManagedPolicy: (arn) => dispatch({ type: "ADD_MANAGED_POLICY", arn }),
    deleteManagedPolicy: (arn) =>
      dispatch({ type: "DELETE_MANAGED_POLICY", arn }),
    addPermissionBoundary: (arn) =>
      dispatch({ type: "ADD_PERMISSION_BOUNDARY", arn }),
    removePermissionBoundary: (arn) =>
      dispatch({ type: "REMOVE_PERMISSION_BOUNDARY", arn }),
    handleManagedPolicySubmit,
    handlePermissionBoundarySubmit,
  };
};

export default useManagedPolicy;
