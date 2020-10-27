import React  from "react";
import {
  Button,
  Dimmer,
  Header,
  Loader,
  Segment,
} from "semantic-ui-react";
import { PolicyProvider, usePolicyContext } from "./hooks/PolicyProvider";
import IAMRolePolicy from "./IAMRolePolicy";
import ResourcePolicy from "./ResourcePolicy";
import ResourceDetail from "./ResourceDetail";
import { DeleteResourceModel } from "./PolicyModals";

const PolicyEditor = () => {
  const {
    isPolicyEditorLoading = true,
    params = {},
    resource = {},
    setToggleDeleteRole,
  } = usePolicyContext();
  const { serviceType = "iamrole" } = params;

  const onDeleteClick = () => setToggleDeleteRole(true);

  const EditPolicy = (serviceType === "iamrole") ? IAMRolePolicy : ResourcePolicy

  return (
      <Dimmer.Dimmable
          as={Segment}
          dimmed={isPolicyEditorLoading}
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
        <ResourceDetail />
        <EditPolicy />
        <DeleteResourceModel />
        <Dimmer
            active={isPolicyEditorLoading}
            inverted
        >
          <Loader />
        </Dimmer>
      </Dimmer.Dimmable>
  );
};

const PolicyEditorWrapper = () => {
  return (
      <PolicyProvider>
        <PolicyEditor />
      </PolicyProvider>
  )
};

export default PolicyEditorWrapper;
