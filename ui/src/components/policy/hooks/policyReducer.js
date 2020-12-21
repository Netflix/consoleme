export const initialState = {
  adminAutoApprove: false,
  context: "inline_policy",
  params: {},
  isPolicyEditorLoading: true,
  resource: {},
  toggleDeleteRole: false,
  toggleRefreshRole: false,
  isSuccess: false,
  togglePolicyModal: false,
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
    case "TOGGLE_REFRESH_ROLE":
      return {
        ...state,
        toggleRefreshRole: action.toggle,
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
      return {
        ...state,
        adminAutoApprove: action.approve,
        togglePolicyModal: true,
      };
    case "SET_CONTEXT":
      return {
        ...state,
        context: action.context,
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
