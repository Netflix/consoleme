export const initialState = {
  actionType: "attach",
  permissionsBoundary: {},
  permissionsBoundaryArn: "",
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_PERMISSIONS_BOUNDARY":
      return {
        ...state,
        permissionsBoundary: action.policy,
      };
    case "ADD_PERMISSIONS_BOUNDARY":
      return {
        ...state,
        actionType: "attach",
        permissionsBoundaryArn: action.arn,
      };
    case "DELETE_PERMISSIONS_BOUNDARY":
      return {
        ...state,
        actionType: "detach",
        permissionsBoundaryArn: action.arn,
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
