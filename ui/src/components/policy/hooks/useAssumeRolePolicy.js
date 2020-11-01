import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./assumeRolePolicyReducer";
import { sendRequestV2 } from "../../../helpers/utils";

const useAssumeRolePolicy = (resource) => {
    const [state, dispatch] = useReducer(reducer, initialState);

    useEffect(() => {
        setAssumeRolePolicy(resource.assume_role_policy_document);
    }, [resource.assume_role_policy_document]);

    const setAssumeRolePolicy = (policy) => {
        dispatch({ type: "SET_ASSUMEROLE_POLICY", policy });
    };

    const handleAssumeRolePolicySubmit = async ({ arn, adminAutoApprove, justification }) => {
        const requestV2 = {
            justification,
            admin_auto_approve: adminAutoApprove,
            changes: {
                changes: [
                    {
                        principal_arn: arn,
                        change_type: "assume_role_policy",
                        policy_name: state.assumeRolePolicy.PolicyName,
                        policy: {
                            policy_document: state.assumeRolePolicy.PolicyDocument,
                        },
                    },
                ],
            },
        };
        return sendRequestV2(requestV2);
    };

    return {
        ...state,
        setAssumeRolePolicy,
        handleAssumeRolePolicySubmit,
    };
};

export default useAssumeRolePolicy;
