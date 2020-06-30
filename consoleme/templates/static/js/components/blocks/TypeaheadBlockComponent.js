import _ from 'lodash';
import React, {Component} from 'react';
import {
    Form,
    Search,
} from 'semantic-ui-react';


class TypeaheadBlockComponent extends Component {
    state = {
        isLoading: false,
        results: [],
        value: '',
    };

    handleResultSelect(e, {result}) {
        this.setState({
            value: result.title,
        }, () => {
            this.props.handleInputUpdate(result.title);
        });
    }

    handleSearchChange(e, {value}) {
        const {typeahead} = this.props;
        this.setState({
            isLoading: true,
            value,
        });

        setTimeout(() => {
            if (this.state.value.length < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        results: [],
                        value: '',
                    }
                );
            }

            const re = new RegExp(_.escapeRegExp(value), 'i');
            const isMatch = (result) => re.test(result.title);

            const TYPEAHEAD_API = typeahead.replace('{query}', value)
            fetch(TYPEAHEAD_API).then((resp) => {
                resp.json().then((source) => {
                    this.setState({
                        isLoading: false,
                        results: _.filter(source, isMatch),
                    });
                });
            });
        }, 300);
    }


    render() {
        const {isLoading, results, value} = this.state;
        const {defaultValue, required, text} = this.props;

        return (
            <Form.Field required={required || false}>
                <label>{text}</label>
                <Search
                    defaultValue={defaultValue || ""}
                    loading={isLoading}
                    onResultSelect={this.handleResultSelect.bind(this)}
                    onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
                        leading: true,
                    })}
                    results={results}
                    value={value}
                />
            </Form.Field>
        );
    }
}

export default TypeaheadBlockComponent;
