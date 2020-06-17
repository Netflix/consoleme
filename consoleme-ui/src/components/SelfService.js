import _ from 'lodash';
import React, {Component} from 'react';
import {
    Button,
    Checkbox,
    Divider,
    Dropdown,
    Feed,
    Form,
    FormDropdown,
    Grid,
    Icon,
    Image,
    Input,
    Label,
    List,
    Header,
    Message,
    Menu,
    Search,
    Segment,
    Select,
    Step,
    TextArea,
} from 'semantic-ui-react';


const buckets = [];
    return {
        key: bucket,
        text: bucket,
        value: bucket,
    };
});

const sourceOptions = [
    { key: 'myApp', text: 'Application', value: 'app' },
    { key: 'myRole', text: 'My Roles', value: 'myRole' },
];

const serviceOptions = [
    { key: 'custom', text: 'Custom Permission (Advanced)', value: 'custom' },
    { key: 'ec2', text: 'EC2 Volmount', value: 'ec2' },
    { key: 'rds', text: 'RDS Database', value: 'rds' },
    { key: 's3', text: 'S3 Bucket', value: 's3' },
    { key: 'ses', text: 'SES - Send Email', value: 'ses' },
    { key: 'sns', text: 'SNS Topic', value: 'sns' },
    { key: 'sqs', text: 'SQS Queue', value: 'sqs' },
    { key: 'sts', text: 'STS AssumeRole', value: 'sts' },
];

const FeedExampleIconLabel = (props) => (
    <Feed>
        <Feed.Event>
            <Feed.Label>
                <Icon name='close' color="pink" />
            </Feed.Label>
            <Feed.Content>
                <Feed.Date>Denied</Feed.Date>
                <Feed.Summary>
                    Target S3 bucket exists in the cross account. You need to assume a role in the cross account using your <a>{props.source}</a> role.
                </Feed.Summary>
                <Feed.Extra text>
                    Please reach out to #security-help for further requests with this details.
                </Feed.Extra>
                <Feed.Meta>
                    <Label size="tiny">
                        <Icon name="tag" />
                        S3
                    </Label>
                    <Label size="tiny" content="Cross Account" />
                </Feed.Meta>
            </Feed.Content>
        </Feed.Event>
        <Feed.Event>
            <Feed.Label>
                <Icon name='close' color="pink" />
            </Feed.Label>
            <Feed.Content>
                <Feed.Date>Denied</Feed.Date>
                <Feed.Summary>
                    The bucket policy is required to allow your role to access the S3 bucket <a>{props.target}</a> exists in the cross account.
                </Feed.Summary>
                <Feed.Extra text>
                    Please reach out to #security-help for further requests with this details.
                </Feed.Extra>
                <Feed.Meta>
                    <Label size="tiny" content="S3" />
                    <Label size="tiny" content="Bucket Policy" />
                </Feed.Meta>
            </Feed.Content>
        </Feed.Event>
        <Feed.Event>
            <Feed.Label>
                <Icon name='checkmark' color="teal"/>
            </Feed.Label>
            <Feed.Content>
                <Feed.Date>Approved</Feed.Date>
                <Feed.Summary>
                    Your role <a>{props.source}</a> already has all the desired permissions for <b>GET</b>, <b>PUT</b> and <b>LIST</b> the bucket <a>{props.target}</a>.
                </Feed.Summary>
            </Feed.Content>
        </Feed.Event>
        <Feed.Event>
            <Feed.Label>
                <Icon name='checkmark' color="teal"/>
            </Feed.Label>
            <Feed.Content>
                <Feed.Date>Approved</Feed.Date>
                <Feed.Summary>
                    There is no Object ACL configured in the S3 bucket <a>{props.target}</a>
                </Feed.Summary>
                <Feed.Meta>
                    <Label size="tiny" content="S3" />
                    <Label size="tiny" content="Object ACL" />
                </Feed.Meta>
            </Feed.Content>
        </Feed.Event>
        <Feed.Event>
            <Feed.Label>
                <Icon name='checkmark' color="teal"/>
            </Feed.Label>
            <Feed.Content>
                <Feed.Date>
                    Approved
                </Feed.Date>
                <Feed.Summary>
                    This S3 bucket <a>{props.target}</a> is shared bucket and has no ownership tag exist.
                </Feed.Summary>
                <Feed.Meta>
                    <Label size="tiny" content="Ownership" />
                </Feed.Meta>
            </Feed.Content>
        </Feed.Event>
    </Feed>
);


const ARN_REGEX = /^arn:aws:iam::(?<account>\d+):role\/(?<role>.+)$/;

class SelfService extends Component {
    state = {
        eligibleRoles: [],
        sourceType: 'app',
        targetType: 's3',
        isLoading: false,
        results: [],
        value: '',
        sourceValue: '',
        targetValue: '',
        role: '',
        account: '',
    };

    componentDidMount() {
        fetch("/api/v1/roles").then((resp) => {
            resp.json().then(({eligible_roles}) => {
                this.setState({
                    eligibleRoles: eligible_roles,
                });
            });
        });
    }

    handleSourceTypeChange(e, {value}) {
        e.preventDefault();
        this.setState({
            sourceType: value,
        });
    }

    handleResultSelect = (searchType, e, { result }) => {
        const isSourceValue = ['app', 'myRole'].some((e) => e === searchType);
        const payload = {};
        const arnMatch = result.title.match(ARN_REGEX);
        if (arnMatch) {
            const {role, account} = arnMatch.groups;
            payload['role'] = role;
            payload['account'] = account;
        }

        if (isSourceValue) {
            payload['sourceValue'] = result.title;
        } else {
            payload['targetValue'] = result.title;
        }
        this.setState(payload);
    };

    handleSearchChange = (searchType, event, { value }) => {
        const isSourceType = ['app', 'myRole'].some((e) => e === searchType);

        const payload = {
            isLoading: true,
        };

        if (isSourceType) {
            payload['sourceValue'] = value;
        } else {
            payload['targetValue'] = value;
        }
        this.setState(payload);

        setTimeout(() => {
            const valueLength = isSourceType
                ? this.state.sourceValue.length
                : this.state.targetValue.length;
            if (valueLength < 1) {
                return this.setState(
                    {
                        isLoading: false,
                        results: [],
                        sourceValue: '',
                        targetValue: '',
                    }
                );
            }

            const re = new RegExp(_.escapeRegExp(value), 'i');
            const isMatch = (result) => re.test(result.title);

            let TYPEAHEAD_API = '/policies/typeahead?resource=' + searchType + '&search=' + value;

            if (!isSourceType) {
                TYPEAHEAD_API += '&account_id=' + this.state.account;
            }

            fetch(TYPEAHEAD_API).then((resp) => {
                resp.json().then((source) => {
                    const filteredResults = _.reduce(
                        source,
                        (memo, data, name) => {
                            const results = _.filter(data.results, isMatch)
                            if (results.length) {
                                memo[name] = { name, results };
                            }
                            return memo;
                        },
                        {},
                    );
                    this.setState({
                        isLoading: false,
                        results: filteredResults,
                    });
                });
            });
        }, 300);
    }

    handleServiceOptionChange(e, {value}) {
        this.setState({
            targetType: value,
        });
    }

    render() {
        const {isLoading, sourceValue, targetValue, results, eligibleRoles, sourceType, targetType} = this.state;
        const roleOptions = eligibleRoles.map((role) => {
            return { key: role, text: role, value: role};
        });

        const sourceTypeSubInput = sourceType === 'app'
            ? (
                <Form.Field required>
                    <label>Choose from Application Roles</label>
                    <Search
                        category
                        loading={isLoading}
                        onResultSelect={this.handleResultSelect.bind(this, sourceType)}
                        onSearchChange={_.debounce(this.handleSearchChange.bind(this, sourceType), 500, {
                            leading: true,
                        })}
                        results={results}
                        value={sourceValue}
                    />
                </Form.Field>
            )
            : (
                <Form.Select
                    required
                    label="Your Eligible Roles"
                    options={roleOptions}
                    search
                    placeholder="Choose Your Role"
                />
            );

        const targetServiceSubInput = targetType === 's3'
            ? (
                <Form.Select
                    required
                    label="Choose a Bucket"
                    options={buckets}
                    search
                    placeholder="Choose a Bucket"
                    defaultValue={targetValue}
                />
            )
            : null;

        const formSourceInputs = (
            <Form>
                <Form.Select
                    required
                    label="Select Source Type"
                    defaultValue={sourceType}
                    options={sourceOptions}
                    placeholder='Select Source Type'
                />
                {sourceTypeSubInput}
                <Form.Checkbox label='Show all entities' checked />
            </Form>
        );

        const formTargetInputs = (
            <Form>
                <Form.Select
                    defaultValue={this.state.targetType}
                    required
                    label="Select AWS Service"
                    options={serviceOptions}
                    placeholder='Choose One'
                    onChange={this.handleServiceOptionChange.bind(this)}
                />
                {targetServiceSubInput}
                <Form.Field>
                    <label>Prefix</label>
                    <input placeholder="/*" defaultValue="/*" />
                </Form.Field>
                <Form.Field>
                    <label>Desired Permissions</label>
                    <Form.Checkbox label='LIST Objects' checked />
                    <Form.Checkbox label='GET Objects' checked />
                    <Form.Checkbox label='PUT Objects' checked />
                    <Form.Checkbox label='DELETE Objects' />
                </Form.Field>
            </Form>
        );

        return (
            <Segment.Group>
                <Segment.Group horizontal>
                    <Segment padded>
                        <Header as="h3" textAlign="left" color='grey'>
                            Step 1: Select Source
                            <Header.Subheader>
                                Please choose a source where permission is required.
                            </Header.Subheader>
                        </Header>
                        <br />
                        {formSourceInputs}
                    </Segment>
                    <Segment padded>
                        <Header as="h3" textAlign="left" color='grey'>
                            Step 2: Select Target
                            <Header.Subheader>
                                Please choose target resources.
                            </Header.Subheader>
                        </Header>
                        <br />
                        {formTargetInputs}
                        <Divider></Divider>
                    </Segment>
                </Segment.Group>
                <Segment padded>
                    <Header as="h3" textAlign="left" color='grey'>
                        Step 3: Review and Submit
                        <Header.Subheader>
                            Please check the below messages for further instructions then submit your request.
                        </Header.Subheader>
                    </Header>
                    <FeedExampleIconLabel source={sourceValue} target={targetValue}/>
                </Segment>
                <Segment>
                    <Button content="Submit" fluid primary disabled />
                </Segment>
            </Segment.Group>
        );
    }
}

export default SelfService;