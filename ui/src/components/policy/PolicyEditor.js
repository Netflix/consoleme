import React from "react";
import {
  Dimmer,
  Divider,
  Grid,
  Header,
  Icon,
  Label,
  Loader,
  Message,
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

  const resourceError = () => {
    if (resource.status) {
      let errorMessage = "";
      try {
        errorMessage = JSON.stringify(resource);
      } catch {
        errorMessage = resource;
      }

      return (
        <Grid padded>
          <Grid.Column width={15}>
            <Message negative>
              <Message.Header>An unexpected error has occurred</Message.Header>
              <p>{errorMessage}</p>
            </Message>
          </Grid.Column>
        </Grid>
      );
    }
  };

  const EditPolicy = ["iamrole", "iamuser"].includes(serviceType)
    ? IAMRolePolicy
    : ResourcePolicy;

  return (
    <Dimmer.Dimmable as={Segment} dimmed={isPolicyEditorLoading}>
      <>
        {resourceError()}
        <Header as="h1" floated="left">
          <Popup
            content="Refresh this resource directly from the cloud"
            trigger={<Icon name="refresh" onClick={onRefreshClick} />}
            position="bottom left"
          />
          Edit Policy for {`${resource.arn || ""}`}
        </Header>
        {["iamrole", "iamuser"].includes(serviceType) &&
        user?.authorization?.can_delete_iam_principals ? (
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
      <Divider />
      <EditPolicy serviceType={serviceType} />
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
