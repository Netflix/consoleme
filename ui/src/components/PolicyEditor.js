import React, { useState } from 'react';
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
    const { accountID, service, resource } = useParams();
    const EditPolicy = getPolicyEditorByService(service);

    return (
        <Segment>
            <>
                <Header as='h1' floated='left'>
                    Edit Policy for arn:aws:iam::609753154238:role/CurtisTestRole
                </Header>
                <Button negative floated="right">
                    Delete
                </Button>
            </>
            <ResourceDetail />
            <EditPolicy />
        </Segment>
    );
}

export default PolicyEditor;