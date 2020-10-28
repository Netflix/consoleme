export const initialState = {
  activeIndex: [],
  isNewPolicy: false,
  adminAutoApprove: false,
  newPolicy: {
    PolicyName: "",
    PolicyDocument: {},
  },
  justification: "",
  requestId: "",
  togglePolicyModal: false,
  inlinePolicies: [],
  policyType: "",
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_POLICIES":
      return {
        ...state,
        activeIndex: [...Array(action.policies.length).keys()],
        inlinePolicies: action.policies,
      };
    case "ADD_POLICY":
      return {
        ...state,
        newPolicy: action.policy,
      };
    case "UPDATE_POLICY":
      return {
        ...state,
        newPolicy: {
          ...action.policy,
          new: false,
        },
      };
    case "DELETE_POLICY":
      return {
        ...state,
        newPolicy: {
          ...action.policy,
          action: "detach",
          new: false,
          PolicyDocument: {
            deleted: true,
          },
        },
      };
    case "SET_ACTIVE_INDEX":
      return {
        ...state,
        activeIndex: action.activeIndex,
      };
    case "SET_IS_NEW_POLICY":
      return {
        ...state,
        isNewPolicy: action.isNewPolicy,
      };
    case "TOGGLE_POLICY_MODAL":
      return {
        ...state,
        togglePolicyModal: action.toggle,
      };
    case "SET_ADMIN_AUTO_APPROVE":
      const { approve = false } = action;
      return {
        ...state,
        adminAutoApprove: approve,
      };
    case "SET_POLICY_TYPE":
      const { policyType = "inline_policy" } = action;
      return {
        ...state,
        policyType: policyType,
      };

    case "SET_JUSTIFICATION":
      return {
        ...state,
        justification: action.justification,
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
