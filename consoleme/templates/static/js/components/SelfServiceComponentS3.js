import _ from 'lodash';
import React, {Component} from 'react';
import {
    Form,
    Header,
    Search,
} from 'semantic-ui-react';

// TODO, get the list of policies from IAM Policy Generator library.
// https://www.npmjs.com/package/iam-policy-generator
const actionOptions = [
    { key: 'list', text: "LIST Objects", value: "list" },
    { key: 'get', text: "GET Objects", value: "get" },
    { key: 'put', text: "PUT Objects", value: "put" },
    { key: 'delete', text: "DELETE Objects", value: "de" },
];


class SelfServiceComponentS3 extends Component {
    static TYPE = 's3';
    static NAME = 'S3 Bucket';

    state = {
        isLoading: false,
        results: [],
    };

    componentDidMount() {
        // initialize a permission state
        this.props.updatePermission({
            type: SelfServiceComponentS3.TYPE,
            actions: [],
            prefix: '/*',
            value: '',
        });
    }

    handleActionChange(e, {value}) {
        const {permission} = this.props;
        this.props.updatePermission({
            actions: value,
            prefix: permission.prefix,
            value: permission.value,
        });
    }

    handleBucketPrefixChange(e) {
        const {permission} = this.props;
        this.props.updatePermission({
            actions: permission.actions,
            prefix: e.target.value,
            value: permission.value,
        });
    }

    handleResultSelect(e, {result}) {
        const {permission} = this.props;
        this.props.updatePermission({
            actions: permission.actions,
            prefix: permission.prefix,
            value: result.title,
        });
    }

    handleSearchChange(e, {value}) {
        const {permission} = this.props;

        this.props.updatePermission({
            actions: permission.actions,
            prefix: permission.prefix,
            value: value,
        });

        this.setState({
            isLoading: true,
        });

        setTimeout(() => {
            const {permission} = this.props;

            if (permission.value.length < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        results: [],
                        value: '',
                    }
                );
            }

            const re = new RegExp(_.escapeRegExp(permission.value), 'i');
            const isMatch = (result) => re.test(result.title);

            const TYPEAHEAD_API = '/policies/typeahead?resource=s3&search=' + permission.value;

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
        const {permission} = this.props;
        const {isLoading, results} = this.state;

        return (
            <Form>
                <Header as="h3">
                    S3 Bucket
                    <Header.Subheader>
                        Please provide the information about the bucket you are trying to access.
                    </Header.Subheader>
                </Header>
                <Form.Field required>
                    <label>Search S3 Bucket</label>
                    <Search
                        loading={isLoading}
                        onResultSelect={this.handleResultSelect.bind(this)}
                        onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
                            leading: true,
                        })}
                        results={results}
                        value={permission.value || ''}
                    />
                </Form.Field>
                <Form.Field>
                    <label>Enter Prefix</label>
                    <input
                        ref="prefix"
                        placeholder="/*"
                        defaultValue="/*"
                        onBlur={this.handleBucketPrefixChange.bind(this)}
                    />
                </Form.Field>
                <Form.Field>
                    <label>Select Actions</label>
                    <Form.Dropdown
                        placeholder="Choose Actions"
                        multiple
                        selection
                        options={actionOptions}
                        value={permission.actions || []}
                        onChange={this.handleActionChange.bind(this)}
                    />
                </Form.Field>
            </Form>
        );
    }
}

export default SelfServiceComponentS3;
