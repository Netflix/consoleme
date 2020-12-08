import React, { useState } from "react";
import { Button, Form, Header, Label } from "semantic-ui-react";
import usePolicyTag from "./hooks/usePolicyTag";
import { JustificationModal } from "./PolicyModals";
import { useAuth } from "../../auth/AuthProviderDefault";

const Tags = () => {
  const { user } = useAuth();
  const {
    arn,
    tags = [],
    isNewTag = false,
    tagChanges = [],
    createTag,
    updateTag,
    deleteTag,
    toggleNewTag,
    handleTagSave,
    setModalWithAdminAutoApprove,
  } = usePolicyTag();

  const [newTag, setNewTag] = useState({ Key: "", Value: "" });

  const onCreateTag = () => toggleNewTag(true);
  const onDeleteTag = (tag) => deleteTag({ arn, tag });
  const onUpdateTag = (originalTag, action, { target: { value } }) => {
    updateTag({
      arn,
      originalTag,
      action,
      value,
    });
  };
  const onSaveTags = () => {
    setModalWithAdminAutoApprove(true);
  };

  const onSubmitTags = () => {
    setModalWithAdminAutoApprove(false);
  };

  const tagList = tags.map((tag) => {
    return (
      <Form.Group key={tag.Key} inline>
        <Form.Input
          label="Key"
          placeholder="Key"
          defaultValue={tag.Key}
          onChange={(e) => onUpdateTag(tag, "update_key", e)}
          disabled={tag.New}
        />
        <Form.Input
          label="Value"
          placeholder="Value"
          defaultValue={tag.Value}
          onChange={(e) => onUpdateTag(tag, "update_value", e)}
          disabled={tag.New}
        />
        <Form.Button
          negative
          icon="remove"
          content="Delete Tag"
          onClick={(e) => onDeleteTag(tag, e)}
        />
      </Form.Group>
    );
  });

  if (isNewTag) {
    tagList.unshift(
      <Form.Group key="newTag" inline>
        <Form.Input
          label="Key"
          placeholder="Key"
          onChange={({ target: { value } }) => {
            setNewTag({ ...newTag, Key: value });
          }}
        />
        <Form.Input
          label="Value"
          placeholder="Value"
          onChange={({ target: { value } }) => {
            setNewTag({ ...newTag, Value: value });
          }}
        />
        <Button.Group>
          <Button
            positive
            icon="add"
            content="Add"
            onClick={() => {
              createTag({ arn, newTag });
              setNewTag({ Key: "", Value: "" });
            }}
          />
          <Button.Or />
          <Button
            negative
            icon="remove"
            content="Cancel"
            onClick={() => toggleNewTag(false)}
          />
        </Button.Group>
      </Form.Group>
    );
  }

  return (
    <>
      <Header as="h2">
        Tags
        <Header.Subheader>
          You can add/edit/delete tags for this role from here.
        </Header.Subheader>
      </Header>
      <Label as="a" attached="top right" color="green" onClick={onCreateTag}>
        Create New Tag
      </Label>
      <Form>
        {tagList}
        <Button.Group attached="bottom">
          {user?.authorization?.can_edit_policies ? (
            <>
              <Form.Button
                positive
                icon="save"
                content="Save"
                onClick={onSaveTags}
                disabled={!tagChanges.length}
              />
              <Button.Or />
            </>
          ) : null}
          <Form.Button
            primary
            icon="send"
            content="Submit"
            onClick={onSubmitTags}
            disabled={!tagChanges.length}
          />
        </Button.Group>
      </Form>
      <JustificationModal handleSubmit={handleTagSave} />
    </>
  );
};

export default Tags;
