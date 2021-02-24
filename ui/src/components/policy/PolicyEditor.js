import React from "react";
import {
  Dimmer,
  Header,
  Icon,
  Label,
  Loader,
  Popup,
  Segment,
} from "semantic-ui-react";
import { PolicyProvider, usePolicyContext } from "./hooks/PolicyProvider";
import IAMRolePolicy from "./IAMRolePolicy";
import ResourcePolicy from "./ResourcePolicy";
import ResourceDetail from "./ResourceDetail";
import { DeleteResourceModal } from "./PolicyModals";
import { useAuth } from "../../auth/AuthProviderDefault";

const PolicyEditor = () => {
  const { user } = useAuth();
  const {
    isPolicyEditorLoading = true,
    params = {},
    resource = {},
    setToggleDeleteRole,
    setToggleRefreshRole,
  } = usePolicyContext();
  const { serviceType = "iamrole" } = params;

  const onDeleteClick = () => setToggleDeleteRole(true);
  const onRefreshClick = () => setToggleRefreshRole(true);

  const EditPolicy = serviceType === "iamrole" ? IAMRolePolicy : ResourcePolicy;

  return (
    <Dimmer.Dimmable as={Segment} dimmed={isPolicyEditorLoading}>
      <>
        <Header as="h1" floated="left">
          <Popup
            content="Refresh this resource directly from the cloud"
            trigger={<Icon name="refresh" onClick={onRefreshClick} />}
            position="bottom left"
          />
          Edit Policy for {`${resource.arn || ""}`}
        </Header>
        {serviceType === "iamrole" && user?.authorization?.can_delete_roles ? (
          <Label
            as="a"
            attached="top right"
            color="red"
            onClick={onDeleteClick}
          >
            Delete
          </Label>
        ) : null}
      </>
      <ResourceDetail />
      <EditPolicy />
      <DeleteResourceModal />
      <Dimmer active={isPolicyEditorLoading} inverted>
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
  );
};

export default PolicyEditorWrapper;
