import React, { useState, useEffect } from "react";
import { Form } from "semantic-ui-react";

const TextInputBlockComponent = (props) => {
  const [value, setValue] = useState("");

  useEffect(() => {
    const { defaultValue } = props;
    setValue(defaultValue || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTextInputChange = (e) => {
    setValue(e.target.value);

    props.handleInputUpdate(props.name, e.target.value);
  };

  const { required, label } = props;

  return (
    <Form.Field required={required}>
      <label>{label || "Enter Value"}</label>
      <input
        onChange={(e) => handleTextInputChange(e)}
        placeholder="Enter your value here"
        value={value}
        type="text"
      />
    </Form.Field>
  );
};

export default TextInputBlockComponent;
