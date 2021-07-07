import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./tagReducer";
import { usePolicyContext } from "./PolicyProvider";

const usePolicyTag = () => {
  const {
    resource = {},
    setModalWithAdminAutoApprove,
    sendRequestV2,
  } = usePolicyContext();
  const [state, dispatch] = useReducer(reducer, initialState);

  const setTags = (tags) => dispatch({ type: "SET_TAGS", tags });
  // IAM resource gets tags from resource.tags
  useEffect(() => {
    if (!resource.tags) {
      return;
    }
    setTags(resource.tags);
  }, [resource.tags]);

  // Other resources get tags from resource resource_details.TagSet.
  useEffect(() => {
    if (!resource.resource_details) {
      return;
    }
    setTags(resource.resource_details.TagSet);
  }, [resource.resource_details]);

  const createTag = ({ arn, newTag }) => {
    const created = {
      principal: {
        principal_arn: arn,
        principal_type: "AwsResource",
      },
      change_type: "resource_tag",
      tag_action: "create",
      key: newTag.Key,
      value: newTag.Value,
    };
    dispatch({ type: "CREATE_TAG", created });
  };
  const deleteTag = ({ arn, tag }) => {
    const deleted = {
      principal: {
        principal_arn: arn,
        principal_type: "AwsResource",
      },
      change_type: "resource_tag",
      tag_action: "delete",
      key: tag.Key,
    };
    dispatch({ type: "DELETE_TAG", deleted });
  };
  const updateTag = ({ arn, originalTag, action, value }) => {
    let changed = {
      principal: {
        principal_arn: arn,
        principal_type: "AwsResource",
      },
      change_type: "resource_tag",
      tag_action: "update",
      original_key: originalTag.Key,
      original_value: originalTag.Value,
    };
    if (action === "update_key") {
      changed = {
        ...changed,
        key: value,
      };
    } else if (action === "update_value") {
      changed = {
        ...changed,
        value,
      };
    } else {
      throw new Error("No such tag action exists");
    }
    dispatch({ type: "UPDATE_TAG", changed });
  };
  const toggleNewTag = (toggle) => dispatch({ type: "TOGGLE_NEW_TAG", toggle });
  const handleTagSave = async ({ adminAutoApprove, justification }) => {
    return sendRequestV2({
      justification,
      admin_auto_approve: adminAutoApprove,
      changes: {
        changes: state.tagChanges,
      },
    });
  };

  return {
    ...state,
    arn: resource.arn,
    setModalWithAdminAutoApprove,
    setTags,
    createTag,
    deleteTag,
    updateTag,
    toggleNewTag,
    handleTagSave,
  };
};

export default usePolicyTag;
