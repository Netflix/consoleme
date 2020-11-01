import React from "react";
import { Header, Segment } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";
import useAssumeRolePolicy from "./hooks/useAssumeRolePolicy";
import { PolicyMonacoEditor } from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";

const AssumeRolePolicy = () => {
    const { resource = {} } = usePolicyContext();
    const {
        assumeRolePolicy = {},
        setAssumeRolePolicy,
        handleAssumeRolePolicySubmit,
    } = useAssumeRolePolicy(resource);

    return (
        <>
            <Header as="h2">
                Assume Role Policy Document
                <Header.Subheader>
                    You can modify this role's assume role policy here.
                </Header.Subheader>
            </Header>
            <Segment
                attached
                style={{
                    border: 0,
                    padding: 0,
                }}
            >
                <PolicyMonacoEditor
                    context="assume_role_policy"
                    policy={assumeRolePolicy}
                    updatePolicy={setAssumeRolePolicy}
                />
            </Segment>
            <JustificationModal
                handleSubmit={handleAssumeRolePolicySubmit}
            />
        </>
    );
};

export default AssumeRolePolicy;
