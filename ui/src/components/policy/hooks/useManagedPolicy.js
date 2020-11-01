import { useEffect, useReducer } from "react";
import { initialState, reducer } from "./managedPolicyReducer";
import { sendRequestV2 } from "../../../helpers/utils";

const useManagedPolicy = (resource) => {
    const [state, dispatch] = useReducer(reducer, initialState);

    useEffect(() => {
        setManagedPolicies(resource.managed_policies);
    }, [resource.managed_policies]);

    const setManagedPolicies = (policies) => {
        dispatch({ type: "SET_MANAGED_POLICIES", policies });
    };

    const addManagedPolicy = (arn) => {
        dispatch({ type: "ADD_MANAGED_POLICY", arn });
    };

    const deleteManagedPolicy = (arn) => {
        dispatch({ type: "DELETE_MANAGED_POLICY", arn });
    };

    const handleManagedPolicySubmit = async ({ arn, adminAutoApprove, justification }) => {
        const requestV2 = {
            justification,
            admin_auto_approve: adminAutoApprove,
            changes: {
                changes: [
                    {
                        principal_arn: arn,
                        arn: state.managedPolicyArn,
                        change_type: "managed_policy",
                        action: state.actionType,
                    },
                ],
            },
        };
        return sendRequestV2(requestV2);
    };

    return {
        ...state,
        setManagedPolicies,
        addManagedPolicy,
        deleteManagedPolicy,
        handleManagedPolicySubmit,
    };
};

export default useManagedPolicy;
