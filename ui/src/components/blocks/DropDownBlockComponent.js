import React, { useState } from "react";
import { Form } from "semantic-ui-react";

const DropDownBlockComponent = (props) => {
  const [actions, setActions] = useState([]);

  const handleActionChange = (e, { value }) => {
    setActions(value);
    props.handleInputUpdate(props.name, value);
  };

  const { defaultValue, options, required } = props;

  return (
    <Form.Field required={required || false}>
      <label>Select Desired Permissions</label>
      <Form.Dropdown
        defaultValue={defaultValue || ""}
        multiple
        onChange={handleActionChange.bind(this)}
        options={options}
        placeholder=""
        selection
        value={actions}
      />
    </Form.Field>
  );
};

export default DropDownBlockComponent;
