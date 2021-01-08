import React, { useState, useEffect } from "react";
import { Form } from "semantic-ui-react";

const TextInputBlockComponent = (props) => {
  const initialState = {
    value: "",
  };
  const [state, setState] = useState(initialState);

  useEffect(() => {
    const { defaultValue } = props;
    this.setState({
      value: defaultValue || "",
    });
  }, []);

  const handleTextInputChange = (e) => {
    const { value } = e.target;
    setState({
      ...state,
      value,
    });
    props.handleInputUpdate(value);
  };

  const { value } = state;
  const { required, label } = props;

  return (
    <Form.Field required={required}>
      <label>{label || "Enter Value"}</label>
      <input
        onChange={() => handleTextInputChange(this)}
        placeholder="Enter your value here"
        value={value}
        type="text"
      />
    </Form.Field>
  );
};

export default TextInputBlockComponent;
