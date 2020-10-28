import React, { useEffect, useState } from "react";
import { Button, Form, Header, Segment } from "semantic-ui-react";
import { usePolicyContext } from "./hooks/PolicyProvider";

const Tags = () => {
    const {
        tags = [],
        isNewTag = false,
        createTag,
        updateTag,
        deleteTag,
        tagChanges,
        toggleNewTag,
    } = usePolicyContext();
    const [newTag, setNewTag] = useState({ Key: "", Value: "" });

    const onCreateTag = () => {
        toggleNewTag(true);
    };

    const onDeleteTag = (key) => {
        deleteTag(key);
    };

    const onUpdateTagValue = (key, { target: { value } }) => {
        updateTag({ Key: key, Value: value });
    };

    const onSaveTags = () => {
        console.log(tagChanges);
    };

    const tagList = tags.map(tag => {
        return (
            <Form.Group key={tag.Key} inline>
                <Form.Input
                    label="Key"
                    placeholder="Key"
                    value={tag.Key}
                    onChange={onUpdateTagValue.bind(this, tag.Key)}
                />
                <Form.Input
                    label="Value"
                    placeholder="Value"
                    defaultValue={tag.Value}
                    onChange={onUpdateTagValue.bind(this, tag.Key)}
                />
                <Form.Button
                    negative
                    icon="remove"
                    content="Delete Tag"
                    onClick={onDeleteTag.bind(this, tag.Key)}
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
                            createTag(newTag);
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
                <Form.Button primary icon="save" content="Save" onClick={onSaveTags} />
            </Form>
        </>
    );
};

export default Tags;
