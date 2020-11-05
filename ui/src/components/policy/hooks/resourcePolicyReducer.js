export const initialState = {
  resourcePolicy: {
    PolicyName: "Resource Policy",
    PolicyDocument: {},
  },
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_RESOURCE_POLICY":
      return {
        ...state,
        resourcePolicy: {
          ...state.resourcePolicy,
          PolicyDocument: action.policy || {},
        },
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
