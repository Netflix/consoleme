import React, { useEffect, useState } from 'react';
import {
    Accordion,
    Button,
    Icon,
    Item,
    Label,
    Header,
    Menu,
    Search,
    Segment,
    Tab,
    Table,
} from 'semantic-ui-react';
import { useParams } from "react-router-dom";
import { sendRequestCommon } from "../helpers/utils";

import IAMRolePolicy from "./IAMRolePolicy";
import ResourcePolicy from "./ResourcePolicy";
import ResourceDetail from "./ResourceDetail";


const getPolicyEditorByService = (service) => {
    switch (service) {
        case 'iamrole': {
            return IAMRolePolicy;
        }
        default: {
            return ResourcePolicy;
        }
    };
};

const PolicyEditor = () => {
    const [resource, setResource] = useState({});
    const { accountID, serviceType, resourceName } = useParams();
    const EditPolicy = getPolicyEditorByService(serviceType);

    useEffect(() => {
        (async () => {
            // TODO, query different endpoint based on serviceType
            const data = await sendRequestCommon(
                null,
                `/api/v2/roles/${accountID}/${resourceName}`,
                "get"
            );
            setResource(data);
        })();
    }, []);

    // TODO, loading until resource data is retrieved
    return (
        <Segment>
            <>
                <Header as='h1' floated='left'>
                    Edit Policy for {`${resource.arn || ''}`}
                </Header>
                <Button negative floated="right">
                    Delete
                </Button>
            </>
            <ResourceDetail resource={resource} />
            <EditPolicy resource={resource} />
        </Segment>
    );
}

export default PolicyEditor;