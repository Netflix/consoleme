export const initialState = {
  actionType: "attach",
  managedPolicies: [],
  managedPolicyArn: "",
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_MANAGED_POLICIES":
      return {
        ...state,
        managedPolicies: action.policies,
      };
    case "ADD_MANAGED_POLICY":
      return {
        ...state,
        actionType: "attach",
        managedPolicyArn: action.arn,
      };
    case "DELETE_MANAGED_POLICY":
      return {
        ...state,
        actionType: "detach",
        managedPolicyArn: action.arn,
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
