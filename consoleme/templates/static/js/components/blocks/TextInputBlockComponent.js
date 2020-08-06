import React, { Component } from "react";
import { Form } from "semantic-ui-react";

class TextInputBlockComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      value: "",
    };
  }

  componentDidMount() {
    const { defaultValue } = this.props;
    this.setState({
      value: defaultValue || "",
    });
  }

  handleTextInputChange(e) {
    const { value } = e.target;
    this.setState(
      {
        value,
      },
      () => {
        this.props.handleInputUpdate(value);
      }
    );
  }

  render() {
    const { value } = this.state;
    const { required, label } = this.props;

    return (
      <Form.Field required={required}>
        <label>{label || "Enter Value"}</label>
        <input
          onChange={this.handleTextInputChange.bind(this)}
          placeholder="Enter your value here"
          value={value}
          type="text"
        />
      </Form.Field>
    );
  }
}

export default TextInputBlockComponent;
