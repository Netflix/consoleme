import React, { Component } from "react";
import { Form } from "semantic-ui-react";

class DropDownBlockComponent extends Component {
  state = {
    actions: [],
  };

  handleActionChange(e, { value }) {
    this.setState(
      {
        actions: value,
      },
      () => {
        this.props.handleInputUpdate(value);
      }
    );
  }

  render() {
    const { actions } = this.state;
    const { defaultValue, options, required } = this.props;

    return (
      <Form.Field required={required || false}>
        <label>Select Desired Permissions</label>
        <Form.Dropdown
          defaultValue={defaultValue || ""}
          multiple
          onChange={this.handleActionChange.bind(this)}
          options={options}
          placeholder=""
          selection
          value={actions}
        />
      </Form.Field>
    );
  }
}

export default DropDownBlockComponent;
