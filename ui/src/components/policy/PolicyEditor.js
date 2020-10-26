import React, { useEffect, useState } from "react";
import {
  Button,
  Dimmer,
  Header,
  Loader,
  Modal,
  Segment,
} from "semantic-ui-react";
import { useParams } from "react-router-dom";
import { sendRequestCommon } from "../../helpers/utils";
import IAMRolePolicy from "./IAMRolePolicy";
import ResourcePolicy from "./ResourcePolicy";
import ResourceDetail from "./ResourceDetail";
import { DeleteResourceModel } from "./PolicyModals";

const PolicyEditor = () => {
  const { accountID, serviceType, region, resourceName } = useParams();
  const [resource, setResource] = useState({});
  const [isLoaderActive, setIsLoaderActive] = useState(true);
  const [toggleDelete, setToggleDelete] = useState(false);

  const onDeleteClick = () => {
    setToggleDelete(true);
  };

  useEffect(() => {
    (async () => {
      const location = ((accountID, serviceType, region, resourceName) => {
        switch (serviceType) {
          case "iamrole": {
            return `/api/v2/roles/${accountID}/${resourceName}`;
          }
          case "s3": {
            return `/api/v2/resources/${accountID}/s3/${resourceName}`;
          }
          case "sqs": {
            return `/api/v2/resources/${accountID}/sqs/${region}/${resourceName}`;
          }
          case "sns": {
            return `/api/v2/resources/${accountID}/sns/${region}/${resourceName}`;
          }
          default: {
            throw new Error("No such service exist");
          }
        }
      })(accountID, serviceType, region, resourceName);
      const data = await sendRequestCommon(null, location, "get");
      setResource(data);
      setIsLoaderActive(false);
    })();
  }, [accountID, region, resourceName, serviceType]);

  const EditPolicy = serviceType === "iamrole" ? IAMRolePolicy :  ResourcePolicy;

  return (
    <Dimmer.Dimmable
        as={Segment}
        dimmed={isLoaderActive}
    >
      <>
        <Header
            as="h1"
            floated="left"
        >
          Edit Policy for {`${resource.arn || ""}`}
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
          resource={resource}
          serviceType={serviceType}
      />
      <EditPolicy
          resource={resource}
      />
      <DeleteResourceModel
          toggle={toggleDelete}
          setToggle={setToggleDelete}
          resource={resource}
      />
      <Dimmer
        active={isLoaderActive}
        inverted
      >
        <Loader />
      </Dimmer>
    </Dimmer.Dimmable>
  );
};

export default PolicyEditor;
