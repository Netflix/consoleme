import _ from 'lodash';
import {generateBasePolicy} from '../helpers/utils';
import React, {Component} from 'react';
import {
    Button,
    Form,
    Header,
    Message,
    Search,
} from 'semantic-ui-react';


class SelfServiceComponentS3 extends Component {
    static TYPE = 's3';
    static NAME = 'S3 Bucket';
    static ACTIONS = [
        {
            key: 'list',
            text: "LIST Objects",
            value: "list",
            actions: [
                "s3:ListBucket",
                "s3:ListBucketVersions"
            ],
        },
        {
            key: 'get',
            text: "GET Objects",
            value: "get",
            actions: [
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:GetObjectVersion",
                "s3:GetObjectVersionTagging",
                "s3:GetObjectAcl",
                "s3:GetObjectVersionAcl"
            ],
        },
        {
            key: 'put',
            text: "PUT Objects",
            value: "put",
            actions: [
                "s3:PutObject",
                "s3:PutObjectTagging",
                "s3:PutObjectVersionTagging",
                "s3:ListMultipartUploadParts*",
                "s3:AbortMultipartUpload",
                "s3:RestoreObject",
            ]
        },
        {
            key: 'delete',
            text: "DELETE Objects",
            value: "delete",
            actions: [
                "s3:DeleteObject",
                "s3:DeleteObjectTagging",
                "s3:DeleteObjectVersion",
                "s3:DeleteObjectVersionTagging",
            ]
        },
    ];

    state = {
        actions: [],
        bucket: '',
        isLoading: false,
        messages: [],
        prefix: '/*',
        results: [],
    };

    handleActionChange(e, {value}) {
        this.setState({
            actions: value,
        });
    }

    handleBucketPrefixChange(e) {
        this.setState({
            prefix: e.target.value,
        });
    }

    handleBucketSelect(e, {result}) {
        this.setState({
            bucket: result.title,
        });
    }

    handleSearchChange(e, {value}) {
        this.setState({
            isLoading: true,
            bucket: value,
        });

        setTimeout(() => {
            if (this.state.bucket.length < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        results: [],
                        bucket: '',
                    }
                );
            }

            const re = new RegExp(_.escapeRegExp(value), 'i');
            const isMatch = (result) => re.test(result.title);

            const TYPEAHEAD_API = '/policies/typeahead?resource=s3&search=' + value;

            fetch(TYPEAHEAD_API).then((resp) => {
                resp.json().then((source) => {
                    // an object with account_id and title
                    this.setState({
                        isLoading: false,
                        results: _.filter(source, isMatch),
                    });
                });
            });
        }, 300);
    }

    handleSubmit() {
        const {actions, bucket} = this.state;

        const messages = [];
        if (!bucket) {
            messages.push("No bucket is selected.")
        }
        if (!actions.length) {
            messages.push("No actions is selected.")
        }
        if (messages.length > 0) {
            return this.setState({
                messages,
            });
        }

        const policy = generateBasePolicy();

        // do some resource clean up specially bucket prefix
        let prefix = this.state.prefix;
        if (prefix && !prefix.endsWith("/*")) {
            prefix = `${prefix}/*`
        } else if (prefix && prefix.endsWith("/*")) {
            prefix = `${prefix}`
        }
        if (!prefix.startsWith("/")) {
            prefix = "/" + prefix
        }

        policy["Resource"] = [
            `arn:aws:s3:::${bucket}`,
            `arn:aws:s3:::${bucket}${prefix}`,
        ];

        actions.forEach(action => {
            const result = _.find(SelfServiceComponentS3.ACTIONS, {"key": action});
            policy["Action"].push(...result.actions);
        });

        const permission = {
            service: SelfServiceComponentS3.TYPE,
            actions,
            policy,
            value: `arn:aws:s3:::${bucket}${prefix}`,
        };
        return this.setState({
            actions: [],
            bucket: '',
            messages: [],
            prefix: '/*',
            results: [],
        }, () => {
            this.props.updatePermission(permission);
        });
    }

    handleKeyUp(e) {
        if (e.keyCode === 13) {
            this.handleSubmit();
        }
    }

    render() {
        const {actions, bucket, isLoading, messages, prefix, results} = this.state;
        const messagesToShow = (messages.length > 0)
            ? (
                <Message negative>
                    <Message.Header>
                        There are some parameters missing.
                    </Message.Header>
                    <Message.List>
                        {
                            messages.map(message => {
                                return <Message.Item>{message}</Message.Item>;
                            })
                        }
                    </Message.List>
                </Message>
            )
            : null;
        return (
            <Form
                onKeyUp={this.handleKeyUp.bind(this)}
            >
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
                        onResultSelect={this.handleBucketSelect.bind(this)}
                        onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
                            leading: true,
                        })}
                        results={results}
                        value={bucket}
                    />
                </Form.Field>
                <Form.Field>
                    <label>Enter Prefix</label>
                    <input
                        onChange={this.handleBucketPrefixChange.bind(this)}
                        placeholder="/*"
                        value={prefix}
                    />
                </Form.Field>
                <Form.Field>
                    <label>Select Actions</label>
                    <Form.Dropdown
                        placeholder="Choose Actions"
                        multiple
                        selection
                        options={SelfServiceComponentS3.ACTIONS}
                        value={actions}
                        onChange={this.handleActionChange.bind(this)}
                    />
                </Form.Field>
                {messagesToShow}
                <Button
                    fluid
                    onClick={this.handleSubmit.bind(this)}
                    primary
                    type='submit'
                >
                    Add Permission
                </Button>
            </Form>
        );
    }
}

export default SelfServiceComponentS3;
