import React, { useState, useCallback, useEffect } from "react";
import { Button, Form, Header, Segment } from "semantic-ui-react";

const Tags = ({ tags = [] }) => {
  const [tagPanels, setTagPanels] = useState([]);
  const [Tags, setTags] = useState(JSON.parse(JSON.stringify(tags)));
  const originalTags = JSON.parse(JSON.stringify(tags));

  const createNewTag = () => {
    Tags.push({
      Key: "",
      Value: "",
    });
    setTags(Tags);
  };
  useEffect(() => {
    setTags(tags);
  }, []); //eslint-disable-line

  useEffect(() => {
    const generatedTagPanels = Tags.map((tag) => {
      return (
        <Form.Group key={tag.Key} inline>
          <Form.Input
            label="Key"
            placeholder="Key"
            defaultValue={tag.Key}
            onChange={(e) => updateTagKey(tag.Key, e)}
          />
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
  }, [Tags, tags]); //eslint-disable-line
  // http://localhost:8081/policies/edit/985081345396/iamrole/consoleme_oss_2_test_admin
  // [{type: "delete_tag", name: "nflxtag-t"}]
  // [{"type":"update_tag","name":"nflxtag-test","value":"test1"},{"type":"update_tag","name":"nflxtag-test2","value":"test2"}]
  // Do not support renaming currently
  const deleteTag = (key, e) => {
    setTags(Tags.filter((tag) => tag.Key !== key));
  };

  const updateTagKey = (originalKey, e) => {
    Tags.forEach((tag) => {
      if (tag.Key === originalKey) {
        tag.Key = e.target.value;
      }
    });
    setTags(Tags);
  };

  const updateTagValue = (originalKey, e) => {
    Tags.forEach((tag) => {
      if (tag.Key === originalKey) {
        tag.Value = e.target.value;
      }
    });
    setTags(Tags);
  };

  const saveTags = (e) => {
    // TODO: Need access to the original tags. Need to do comparison against `Tags`. Need to compile appropriate
    // change model

    console.log(Tags);
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
