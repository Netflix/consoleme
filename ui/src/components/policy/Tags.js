import React, { useState, useCallback, useEffect } from "react";
import { Button, Form, Header, Segment } from "semantic-ui-react";

const Tags = ({ tags = [] }) => {
  const [updatedTags, setUpdatedTags] = useState({});
  const [tagPanels, setTagPanels] = useState([]);
  const [newTags, setNewTags] = useState(tags);

  const createNewTag = () => {
    console.log(newTags);
    newTags.push({
      Key: "",
      Value: "",
    });
    setNewTags(newTags);
  };
  useEffect(() => {
    setNewTags(tags);
  }, []); //eslint-disable-line

  useEffect(() => {
    const generatedTagPanels = newTags.map((tag) => {
      return (
        <Form.Group key={tag.Key} inline>
          <Form.Input label="Key" placeholder="Key" defaultValue={tag.Key} />
          <Form.Input
            label="Value"
            placeholder="Value"
            defaultValue={tag.Value}
            onChange={(e) => updateTagValue(tag.Key, e)}
          />
          <Form.Button
            negative
            icon="remove"
            content="Delete Tag"
            onClick={() => deleteTag(tag.Key)}
          />
        </Form.Group>
      );
    });
    setTagPanels(generatedTagPanels);
  }, [newTags]); //eslint-disable-line
  // http://localhost:8081/policies/edit/985081345396/iamrole/consoleme_oss_2_test_admin
  // [{type: "delete_tag", name: "nflxtag-t"}]
  // [{"type":"update_tag","name":"nflxtag-test","value":"test1"},{"type":"update_tag","name":"nflxtag-test2","value":"test2"}]
  // Do not support renaming currently
  const deleteTag = (key) => {
    console.log(key);
  };

  const updateTagValue = (key, e) => {
    console.log(key, e);
    console.log(e.target.value);
    updatedTags[key] = e.target.value;
    setUpdatedTags(updatedTags);
  };

  const saveTags = (e) => {
    console.log(e);
  };
  // TODO, add expand all, close all features
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
          <Button positive onClick={createNewTag}>
            Create New Tag
          </Button>
        </Button.Group>
      </Segment>
      <Form>
        {tagPanels}
        <Form.Button primary icon="save" content="Save" onClick={saveTags} />
      </Form>
    </>
  );
};

export default Tags;
