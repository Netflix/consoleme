import React, { useState } from "react";
import { Form } from "semantic-ui-react";

const DropDownBlockComponent = (props) => {
  const initialState = {
    actions: [],
  };

  const [state, setState] = useState(initialState);

  const handleActionChange = (e, { value }) => {
    setState({
      ...state,
      actions: value,
    });
    props.handleInputUpdate(value);
  };

  const { actions } = state;
  const { defaultValue, options, required } = props;

  return (
    <Form.Field required={required || false}>
      <label>Select Desired Permissions</label>
      <Form.Dropdown
        defaultValue={defaultValue || ""}
        multiple
        onChange={() => handleActionChange(this)}
        options={options}
        placeholder=""
        selection
        value={actions}
      />
    </Form.Field>
  );
};

export default DropDownBlockComponent;
