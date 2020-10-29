export const initialState = {
  adminAutoApprove: false,
  params: {},
  isPolicyEditorLoading: true,
  resource: {},
  toggleDeleteRole: false,
  isSuccess: false,
  justification: "",
  togglePolicyModal: false,
  policyType: "",
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "UPDATE_PARAMS":
      return {
        ...state,
        params: action.params,
      };
    case "UPDATE_RESOURCE":
      return {
        ...state,
        resource: action.resource,
      };
    case "TOGGLE_LOADING":
      return {
        ...state,
        isPolicyEditorLoading: action.loading,
      };
    case "TOGGLE_DELETE_ROLE":
      return {
        ...state,
        toggleDeleteRole: action.toggle,
      };
    case "SET_IS_SUCCESS":
      return {
        ...state,
        isSuccess: action.isSuccess,
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
