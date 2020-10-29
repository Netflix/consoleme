import { useReducer } from "react";
import { initialState, reducer } from "./tagReducer";
import { sendRequestCommon } from "../../../helpers/utils";

const usePolicyTag = () => {
    const [state, dispatch] = useReducer(reducer, initialState);

    const setTags = (tags) => dispatch({ type: "SET_TAGS", tags });
    const createTag = ({ arn, newTag }) => {
        const created = {
            principal_arn: arn,
            change_type: "resource_tag",
            tag_action: "create",
            key: newTag.Key,
            value: newTag.Value,
        };
        dispatch({ type: "CREATE_TAG", created });
    };
    const deleteTag = ({ arn, tag }) => {
        const deleted = {
            principal_arn: arn,
            change_type: "resource_tag",
            tag_action: "delete",
            key: tag.Key,
        }
        dispatch({ type: "DELETE_TAG", deleted });
    }
    const updateTag = ({ arn, originalTag, action, value }) => {
        let changed = {
            principal_arn: arn,
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
    }
    const toggleNewTag = (toggle) => dispatch({ type: "TOGGLE_NEW_TAG", toggle });
    const handleTagSave = async ({ arn, adminAutoApprove, justification }) => {
        const requestV2 = {
            justification,
            admin_auto_approve: adminAutoApprove,
            changes: {
                changes: state.tagChanges,
            },
        };

        const response = await sendRequestCommon(requestV2, "/api/v2/request");

        if (response) {
            const { request_created, request_id, request_url, errors } = response;
            if (request_created === true) {
                if (adminAutoApprove && errors === 0) {
                    return {
                        message: `Successfully created and applied request: [${request_id}](${request_url}).`,
                        request_created,
                        error: false,
                    };
                } else if (errors === 0) {
                    return {
                        message: `Successfully created request: [${request_id}](${request_url}).`,
                        request_created,
                        error: false,
                    };
                } else {
                    return {
                        message: `This request was created and partially successful: : [${request_id}](${request_url}). But the server reported some errors with the request: ${JSON.stringify(
                            response
                        )}`,
                        request_created,
                        error: true,
                    };
                }
            }
            return {
                message: `Server reported an error with the request: ${JSON.stringify(
                    response
                )}`,
                request_created,
                error: true,
            };
        } else {
            return {
                message: `"Failed to submit request: ${JSON.stringify(response)}`,
                request_created: false,
                error: true,
            };
        }
    };

    return {
        ...state,
        setTags,
        createTag,
        deleteTag,
        updateTag,
        toggleNewTag,
        handleTagSave,
    };
};

export default usePolicyTag;
