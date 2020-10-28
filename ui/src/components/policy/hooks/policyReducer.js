export const initialState = {
  params: {},
  isPolicyEditorLoading: true,
  resource: {},
  toggleDeleteRole: false,
  isSuccess: false,
  tags: [],
  isNewTag: false,
  tagChanges: [],
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
    case "SET_TAGS":
      return {
        ...state,
        tags: action.tags,
      };
    case "TOGGLE_NEW_TAG":
      return {
        ...state,
        isNewTag: action.toggle,
      };
    case "CREATE_TAG":
      return {
        ...state,
        isNewTag: false,
        tags: [{ Key: action.tag.Key, Value: action.tag.Value }, ...state.tags],
        tagChanges: [
          ...state.tagChanges.filter(change => change.name !== action.tag.Key),
          { type: "create_tag", name: action.tag.Key, value: action.tag.Value },
        ],
      };
    case "DELETE_TAG":
      const newChanges = [...state.tagChanges, { type: "delete_tag", name: action.key }];
      // check if there were newly created tags but deleted before save.
      const removeItems = newChanges.map(change => {
        if (change.type === "create_tag" && change.name === action.key) {
          return change.name;
        }
      });

      return {
        ...state,
        tags: [...state.tags.filter(tag => tag.Key !== action.key)],
        tagChanges: newChanges.filter(change => !removeItems.includes(change.name))
      };
    case "UPDATE_TAG":
      return {
        ...state,
        tagChanges: [
          ...state.tagChanges.filter(change => change.name !== action.tag.Key),
          { type: "update_tag", name: action.tag.Key, value: action.tag.Value },
        ],
      };
    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
