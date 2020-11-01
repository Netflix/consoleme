import React from "react";
import { Header, Segment } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";
import useResourcePolicy from "./hooks/useResourcePolicy";
import { PolicyMonacoEditor } from "./PolicyMonacoEditor";
import { JustificationModal } from "./PolicyModals";

const ResourcePolicyEditor = () => {
    const { resource = {} } = usePolicyContext();
    const {
        resourcePolicy = {},
        setResourcePolicy,
        handleResourcePolicySubmit,
    } = useResourcePolicy(resource);

    return (
        <>
            <Header as="h2">
                Resource Policy
                <Header.Subheader>
                    You can add/edit/delete resource policy here.
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
                    context="resource_policy"
                    policy={resourcePolicy}
                    updatePolicy={setResourcePolicy}
                />
            </Segment>
            <JustificationModal
                handleSubmit={handleResourcePolicySubmit}
            />
        </>
    );
};

export default ResourcePolicyEditor;
