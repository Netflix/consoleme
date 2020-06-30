import React, {Component} from 'react';
import {
    Form,
} from 'semantic-ui-react';


class TextInputBlockComponent extends Component {
    state = {
        value: '',
    };

    handleTextInputChange(e) {
        const {value} = e.target;
        this.setState({
            value,
        }, () => {
            this.props.handleInputUpdate(value);
        });
    }

    render() {
        const {value} = this.state;
        const {defaultValue, required, text} = this.props;

        return (
            <Form.Field required={required}>
                <label>{text}</label>
                <input
                    defaultValue={defaultValue}
                    onChange={this.handleTextInputChange.bind(this)}
                    placeholder="Enter your value here"
                    value={value || (defaultValue || '')}
                    type="text"
                />
            </Form.Field>
        );
    }
}

export default TextInputBlockComponent;
