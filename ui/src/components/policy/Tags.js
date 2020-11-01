import React, { useState } from "react";
import { Button, Form, Header, Segment } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";
import usePolicyTag from "./hooks/usePolicyTag";
import { JustificationModal } from "./PolicyModals";

const Tags = () => {
    const {
        resource = {},
        setAdminAutoApprove,
        setTogglePolicyModal,
    } = usePolicyContext();

    const {
        tags = [],
        isNewTag = false,
        tagChanges = [],
        createTag,
        updateTag,
        deleteTag,
        toggleNewTag,
        handleTagSave,
    } = usePolicyTag(resource);

    const { arn } = resource;
    const [newTag, setNewTag] = useState({ Key: "", Value: "" });

    const onCreateTag = () => toggleNewTag(true);
    const onDeleteTag = (tag) => deleteTag({ arn, tag });
    const onUpdateTag = ( originalTag, action, { target: { value } }) => {
        updateTag({
            arn,
            originalTag,
            action,
            value,
        });
    };
    const onSaveTags = () => {
        setAdminAutoApprove(true);
        setTogglePolicyModal(true);
    };

    const tagList = tags.map(tag => {
        return (
            <Form.Group
                key={tag.Key}
                inline
            >
                <Form.Input
                    label="Key"
                    placeholder="Key"
                    defaultValue={tag.Key}
                    onChange={onUpdateTag.bind(this, tag, 'update_key')}
                    disabled={tag.New}
                />
                <Form.Input
                    label="Value"
                    placeholder="Value"
                    defaultValue={tag.Value}
                    onChange={onUpdateTag.bind(this, tag, 'update_value')}
                    disabled={tag.New}
                />
                <Form.Button
                    negative
                    icon="remove"
                    content="Delete Tag"
                    onClick={onDeleteTag.bind(this, tag)}
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
                    onChange={({ target: { value }}) => {
                        setNewTag({ ...newTag, Key: value });
                    }}
                />
                <Form.Input
                    label="Value"
                    placeholder="Value"
                    onChange={({ target: { value }}) => {
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
        )
    }

    return (
        <>
            <Segment
                basic
                clearing
                style={{
                    padding: 0,
                }}
            >
                <Header as="h2" floated="left">
                    Tags
                    <Header.Subheader>
                        You can add/edit/delete tags for this role from here.
                    </Header.Subheader>
                </Header>
                <Button.Group floated="right">
                    <Button positive onClick={onCreateTag}>
                        Create New Tag
                    </Button>
                </Button.Group>
            </Segment>
            <Form>
                {tagList}
                <Form.Button
                    primary
                    icon="save"
                    content="Save"
                    onClick={onSaveTags}
                    disabled={!tagChanges.length}
                />
            </Form>
            <JustificationModal
                handleSubmit={handleTagSave}
            />
        </>
    );
};

export default Tags;
