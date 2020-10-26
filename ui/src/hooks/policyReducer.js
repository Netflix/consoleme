export const initialState = {
  adminAutoApprove: false,
  currentPolicies: [],
  newPolicy: {
    PolicyName: "",
    PolicyDocument: {},
  },
  justification: "",
  requestId: "",
};

export const reducer = (state, action) => {
  const { policy } = action;
  switch (action.type) {
    case "UPDATE_POLICY":
      const newPolicies = state.currentPolicies.map((p) => {
        return p.PolicyName === policy.PolicyName ? policy : p;
      });
      policy.new = false;
      return {
        ...state,
        newPolicy: policy,
        currentPolicies: newPolicies,
      };
    case "ADD_POLICY":
      const { newPolicy = {} } = action;
      return {
        ...state,
        newPolicy,
        currentPolicies: [...state.currentPolicies, newPolicy],
      };
    case "REMOVE_POLICY":
      return {
        ...state,
        newPolicy: {
          PolicyName: "",
          PolicyDocument: {},
        },
        currentPolicies: [
          ...state.currentPolicies.filter(
            (p) => p.PolicyName !== state.newPolicy.PolicyName
          ),
        ],
      };
    case "DELETE_POLICY":
      policy.action = "detach";
      policy.new = false;
      policy.PolicyDocument = {
        deleted: true,
      };
      return {
        ...state,
        newPolicy: policy,
      };
    case "UPDATE_INLINE_POLICIES":
      const { policies = [] } = action;
      return {
        ...state,
        currentPolicies: policies,
      };
    case "SET_ADMIN_AUTO_APPROVE":
      const { approve = false } = action;
      return {
        ...state,
        adminAutoApprove: approve,
      };
    case "SET_JUSTIFICATION":
      const { justification = "" } = action;
      return {
        ...state,
        justification,
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
