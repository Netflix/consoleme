export const initialState = {
  activeIndex: [],
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
          activeIndex: [...Array(action.policies.length).keys()],
          inlinePolicies: action.policies,
          isNewPolicy: false,
        };
      } else {
        return {
          ...state,
          isNewPolicy: false,
        };
      }
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
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
