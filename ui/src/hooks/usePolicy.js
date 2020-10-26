import { useCallback, useEffect, useReducer } from "react";
import { initialState, reducer } from "./policyReducer";
import { sendRequestCommon } from "../helpers/utils";

export const useInlinePolicy = ({ arn, policies = [] }) => {
    const [state, dispatch] = useReducer(reducer, initialState);
    const { adminAutoApprove, currentPolicies, justification, newPolicy } = state;

    useEffect(() => {
        setPolicies(policies);
    }, [policies]);

    const setPolicies = (policies) => dispatch({type: 'UPDATE_INLINE_POLICIES', policies});

    const handlePolicySubmit = useCallback(async () => {
        // adminAutoApprove, newPolicyName, newPolicy are updated from the PolicyMonacoEditor.
        // justification is updated from the PolicyModals.
        const requestV2 = {
            justification,
            admin_auto_approve: adminAutoApprove,
            changes: {
                changes: [
                    {
                        principal_arn: arn,
                        change_type: "inline_policy",
                        policy_name: newPolicy.PolicyName,
                        action: "attach",
                        policy: {
                            policy_document: newPolicy.PolicyDocument,
                        },
                    },
                ],
            },
        };

        const response = await sendRequestCommon(requestV2, "/api/v2/request");

        if (response) {
            const {request_created, request_id, request_url} = response;
            if (request_created === true) {
                if (adminAutoApprove) {
                    return {
                        message: `Successfully created and applied request: [${request_id}](${request_url}).`,
                        request_created,
                    };
                } else {
                    return {
                        message: `Successfully created request: [${request_id}](${request_url}).`,
                        request_created,
                    };
                }
            }
            return {
                message: `Server reported an error with the request: ${JSON.stringify(response)}`,
                request_created,
            };
        } else {
            return {
                message: `"Failed to submit request: ${JSON.stringify(response)}`,
                request_created: false,
            };
        }
    }, [newPolicy]);

    return {
        adminAutoApprove,
        setAdminAutoApprove: (approve) => dispatch({ type: 'SET_ADMIN_AUTO_APPROVE', approve: true }),
        currentPolicies,
        setPolicies,
        updatePolicy: (policy) => dispatch({ type: 'UPDATE_POLICY', policy }),
        addPolicy: (newPolicy) => dispatch({ type: 'ADD_POLICY', newPolicy }),
        removePolicy: (removePolicy) => dispatch({ type: 'REMOVE_POLICY', removePolicy }),
        justification,
        setJustification: (justification) => dispatch({ type: "SET_JUSTIFICATION", justification}),
        handlePolicySubmit,
    };
};
