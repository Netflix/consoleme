/* eslint-disable no-case-declarations */
export const initialState = {
  tags: [],
  isNewTag: false,
  tagChanges: [],
};

export const reducer = (state, action) => {
  switch (action.type) {
    case "SET_TAGS":
      return {
        ...state,
        tags: action.tags || [],
        tagChanges: [],
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
        tags: [
          { Key: action.created.key, Value: action.created.value, New: true },
          ...state.tags,
        ],
        tagChanges: [...state.tagChanges, action.created],
      };
    case "DELETE_TAG":
      const newChanges = [...state.tagChanges, action.deleted];
      // check if there were newly created tags but deleted before save.
      const createdTags = newChanges.reduce((created, change) => {
        if (
          change.tag_action === "create" &&
          change.key === action.deleted.key
        ) {
          created.push(change.key);
        }
        return created;
      }, []);
      return {
        ...state,
        tags: [...state.tags.filter((tag) => tag.Key !== action.deleted.key)],
        tagChanges: newChanges.filter(
          (change) => !createdTags.includes(change.key)
        ),
      };
    case "UPDATE_TAG":
      const matched = state.tagChanges.filter(
        (change) => change.original_key === action.changed.original_key
      );
      // TODO, check if the given value is back to the same as original tag.
      if (matched.length > 0) {
        return {
          ...state,
          tagChanges: state.tagChanges.map((change) => {
            // if there are already change exist with same original key then update or override
            if (change.original_key === action.changed.original_key) {
              return {
                ...change,
                ...action.changed,
              };
            }
            return change;
          }),
        };
      }
      return {
        ...state,
        tagChanges: [...state.tagChanges, action.changed],
      };

    default:
      throw new Error(`No such action type ${action.type} exist`);
  }
};
