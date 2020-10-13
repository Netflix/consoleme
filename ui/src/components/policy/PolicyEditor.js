import React, { useEffect, useState } from 'react';
import {
    Button,
    Dimmer,
    Header,
    Loader,
    Modal,
    Segment,
} from 'semantic-ui-react';
import { useParams } from "react-router-dom";
import { sendRequestCommon } from "../../helpers/utils";

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
    const { accountID, serviceType, region, resourceName } = useParams();

    const [resource, setResource] = useState({});
    const [isActive, setIsActive] = useState(true);
    const [open, setOpen] = useState(false);

    const EditPolicy = getPolicyEditorByService(serviceType);

    const onDeleteClick = () => {
        setOpen(true);
    };

    useEffect(() => {
        (async () => {
            // TODO, query different endpoint based on serviceType
            const location = ((accountID, serviceType, region, resourceName) => {
                switch (serviceType) {
                    case 'iamrole': {
                        return `/api/v2/roles/${accountID}/${resourceName}`;
                    }
                    case 's3': {
                        return `/api/v2/resources/${accountID}/s3/${resourceName}`;
                    }
                    case 'sqs': {
                        return `/api/v2/resources/${accountID}/sqs/${region}/${resourceName}`;
                    }
                    case 'sns': {
                        return `/api/v2/resources/${accountID}/sns/${region}/${resourceName}`;
                    }
                    default: {
                        throw "No such service exist";
                    }
                }
            })(accountID, serviceType, region, resourceName);
            const data = await sendRequestCommon(null, location, "get");
            setResource(data);
            setIsActive(false);
        })();
    }, []);

    return (
        <Dimmer.Dimmable as={Segment} dimmed={isActive}>
            <>
                <Header as='h1' floated='left'>
                    Edit Policy for {`${resource.arn || ''}`}
                </Header>
                <Button
                    negative
                    floated="right"
                    onClick={onDeleteClick}
                >
                    Delete
                </Button>
            </>
            <ResourceDetail
                serviceType={serviceType}
                resource={resource}
            />
            <EditPolicy resource={resource} />
            <Modal
                onClose={() => setOpen(false)}
                onOpen={() => setOpen(true)}
                open={open}
            >
                <Modal.Header>Deleting the role {resource.name}</Modal.Header>
                <Modal.Content image>
                    <Modal.Description>
                        <p>Are you sure to delete this role?</p>
                    </Modal.Description>
                </Modal.Content>
                <Modal.Actions>
                    <Button
                        content="Delete"
                        labelPosition='left'
                        icon='remove'
                        onClick={() => setOpen(false)}
                        negative
                    />
                    <Button
                        onClick={() => setOpen(false)}
                    >
                        Cancel
                    </Button>

                </Modal.Actions>
            </Modal>
            <Dimmer inverted active={isActive}>
                <Loader />
            </Dimmer>
        </Dimmer.Dimmable>
    );
}

export default PolicyEditor;