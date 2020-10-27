export const initialState = {
  params: {},
  isPolicyEditorLoading: true,
  resource: {},
  toggleDeleteRole: false,
  isSuccess: false,
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
      }
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
