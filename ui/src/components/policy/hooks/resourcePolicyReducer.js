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
                resourcePolicy: action.policy || state.resourcePolicy,
            };
        default:
            throw new Error(`No such action type ${action.type} exist`);
    }
};
