export const initialState = {
  isNewPolicy: false,
  newPolicy: {
    PolicyName: "",
    PolicyDocument: {},
  },
  inlinePolicies: [],
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_POLICIES":
      if (action.policies) {
        return {
          ...state,
          inlinePolicies: action.policies,
          isNewPolicy: false,
        };
      }
      return {
        ...state,
        isNewPolicy: false,
      };
    case "ADD_POLICY":
      return {
        ...state,
        isNewPolicy: false,
        newPolicy: action.policy,
      };
    case "UPDATE_POLICY":
      return {
        ...state,
        isNewPolicy: false,
        newPolicy: {
          ...action.policy,
          new: false,
        },
      };
    case "DELETE_POLICY":
      return {
        ...state,
        isNewPolicy: false,
        newPolicy: {
          ...action.policy,
          action: "detach",
          new: false,
          PolicyDocument: {
            deleted: true,
          },
        },
      };
    case "SET_IS_NEW_POLICY":
      return {
        ...state,
        isNewPolicy: action.isNewPolicy,
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
