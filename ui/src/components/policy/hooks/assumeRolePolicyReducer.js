export const initialState = {
  assumeRolePolicy: {
    PolicyName: "Assume Role Policy Document",
    PolicyDocument: {},
  },
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_ASSUMEROLE_POLICY":
      return {
        ...state,
        assumeRolePolicy: {
          ...state.assumeRolePolicy,
          PolicyDocument: action.policy,
        },
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
