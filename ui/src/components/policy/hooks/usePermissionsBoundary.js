import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./permissionsBoundaryReducer";
import { usePolicyContext } from "./PolicyProvider";

const usePermissionsBoundary = () => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const {
    params = {},
    resource = {},
    setModalWithAdminAutoApprove,
    sendRequestV2,
  } = usePolicyContext();

  useEffect(() => {
    dispatch({
      type: "SET_PERMISSIONS_BOUNDARY",
      policy: resource.permissions_boundary,
    });
  }, [resource.permissions_boundary]);

  const handlePermissionsBoundarySubmit = async ({
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
            arn: state.permissionsBoundaryArn,
            change_type: "permissions_boundary",
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
    setPermissionsBoundary: (policy) =>
      dispatch({
        type: "SET_PERMISSIONS_BOUNDARY",
        policy,
      }),
    resource: resource,
    addPermissionsBoundary: (arn) =>
      dispatch({ type: "ADD_PERMISSIONS_BOUNDARY", arn }),
    deletePermissionsBoundary: (arn) =>
      dispatch({ type: "DELETE_PERMISSIONS_BOUNDARY", arn }),
    handlePermissionsBoundarySubmit,
  };
};

export default usePermissionsBoundary;
