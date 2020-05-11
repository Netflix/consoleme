import _ from 'lodash';
import React, {Component} from 'react';
import ReactDOM from 'react-dom';
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


const buckets = ["ap-northeast-1-441660064727-s3-access-logs", "ap-northeast-2-441660064727-s3-access-logs", "ap-south-1-441660064727-s3-access-logs", "ap-southeast-1-441660064727-s3-access-logs", "ap-southeast-2-441660064727-s3-access-logs", "ca-central-1-441660064727-s3-access-logs", "cf-templates-ek0ovumwslho-us-west-2", "codepipeline-us-east-1-949857809385", "eu-central-1-441660064727-s3-access-logs", "eu-north-1-441660064727-s3-access-logs", "eu-west-1-441660064727-s3-access-logs", "eu-west-1.netflix-logs-bunkerprod", "eu-west-2-441660064727-s3-access-logs", "eu-west-3-441660064727-s3-access-logs", "netflix-logs-bunker-prod", "netflix-logs-bunker-prod-eu-west-1", "netflix-logs-bunker-prod-us-east-1", "netflix-logs-bunker-prod-us-west-1", "netflix-logs-bunker-prod-us-west-2", "netflix-logs-bunkerprod", "netflix-logs-bunkerprod-eu-west-1", "netflix-logs-bunkerprod-us-west-1", "netflix-logs-bunkerprod-us-west-2", "nflx-alert-sqs-to-otterspeak-lambda.bunkerprod.eu-west-1", "nflx-alert-sqs-to-otterspeak-lambda.bunkerprod.us-east-1", "nflx-alert-sqs-to-otterspeak-lambda.bunkerprod.us-west-2", "nflx-apiprotect-bunkerprod-us-west-2", "nflx-awsconfig-bunkerprod-ap-northeast-1", "nflx-awsconfig-bunkerprod-ap-northeast-2", "nflx-awsconfig-bunkerprod-ap-south-1", "nflx-awsconfig-bunkerprod-ap-southeast-1", "nflx-awsconfig-bunkerprod-ap-southeast-2", "nflx-awsconfig-bunkerprod-ca-central-1", "nflx-awsconfig-bunkerprod-eu-central-1", "nflx-awsconfig-bunkerprod-eu-north-1", "nflx-awsconfig-bunkerprod-eu-west-1", "nflx-awsconfig-bunkerprod-eu-west-2", "nflx-awsconfig-bunkerprod-eu-west-3", "nflx-awsconfig-bunkerprod-sa-east-1", "nflx-awsconfig-bunkerprod-us-east-1", "nflx-awsconfig-bunkerprod-us-east-2", "nflx-awsconfig-bunkerprod-us-west-1", "nflx-awsconfig-bunkerprod-us-west-2", "nflx-consoleme-api.elb.logs-bunkerprod-us-east-1", "nflx-consoleme-api.elb.logs-bunkerprod-us-west-2", "nflx-consoleme-bunkerprod-us-west-2", "nflx-consoleme.elb.logs-bunkerprod-us-east-1", "nflx-consoleme.elb.logs-bunkerprod-us-west-2", "nflx-historical-reports-bunkerprod-eu-west-1", "nflx-historical-reports-bunkerprod-us-east-1", "nflx-historical-reports-bunkerprod-us-west-2", "nflx-honeybee-bunker-prod-us-west-2", "nflx-honeybee-pipeline-bunker-prod-us-west-2", "nflx-infrasec-codepipeline-bunker-prod-us-east-1", "nflx-infrasec-codepipeline-bunker-prod-us-west-2", "nflx-infrasec-lambdas-bunkerprod-us-east-1", "nflx-infrasec-lambdas-bunkerprod-us-west-2", "nflx-migrator-iamrole-lambda", "nflx-remotelambdarolecreator.bunkerprod.eu-west-1", "nflx-remotelambdarolecreator.bunkerprod.us-east-1", "nflx-remotelambdarolecreator.bunkerprod.us-west-2", "nflx-repokid-bunker-prod-us-west-2", "nflx-roleprotect-bunker-prod-us-west-2", "nflx-terraform-bunkerprod-us-east-1", "nflx-terraform-bunkerprod-us-west-2", "nflx-user-role-creator-lambda.bunkerprod.us-east-1", "nflx-user-role-creator-lambda.bunkerprod.us-west-2", "nflx-vault-bunker-prod-us-east-1", "nflx-vault-bunker-prod-us-west-2", "sa-east-1-441660064727-s3-access-logs", "us-east-1-441660064727-s3-access-logs", "us-east-1-bunkerprod-nflx-secops-lambdas", "us-east-1.netflix-logs-bunkerprod", "us-east-2-441660064727-s3-access-logs", "us-west-1-441660064727-s3-access-logs", "us-west-2-441660064727-s3-access-logs", "us-west-2-bunkerprod-nflx-secops-lambdas", "us-west-2.netflix-logs-bunkerprod"].map(bucket => {
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
        targetType: '',
        isLoading: false,
        results: [],
        value: '',
        sourceValue: '',
        targetValue: '',
        actionList: [],
        role: '',
        account: '',
        policyList: [],
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

    handleSubTargetChange(e, {value}) {
        this.setState({
            targetValue: value,
        });
    }

    handleActionChange(e, {value}) {
        this.setState({
           actionList: value,
        });
    }

    handlePolicyAdd(e, {value}) {
        const {targetType, targetValue, actionList} = this.state;
        const prefix = this.refs.prefix.value;
        const policyList = this.state.policyList;

        if (targetValue == '' || !actionList.length) {
            return;
        }

        policyList.push({
            targetType,
            targetValue,
            actionList,
            prefix,
        });

        this.setState({
            targetType: 's3',
            targetValue: '',
            actionList: [],
            prefix: '/*',
            policyList,
        });
    }

    handlePolicyDelete(targetPolicy, event, value) {
        const policyList = this.state.policyList.filter(policy => {
           return policy.targetValue != targetPolicy.targetValue;
        });

        this.setState({ policyList });
    }

    render() {
        const {actionList, isLoading, sourceValue, targetValue, results, eligibleRoles, sourceType, targetType} = this.state;
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
                    value={targetValue}
                    onChange={this.handleSubTargetChange.bind(this)}
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

        const actionOptions = [
            { key: 'list', text: "LIST Objects", value: "list" },
            { key: 'get', text: "GET Objects", value: "get" },
            { key: 'put', text: "PUT Objects", value: "put" },
            { key: 'delete', text: "DELETE Objects", value: "de" },
        ]

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
                    <label>Enter Prefix</label>
                    <input ref="prefix" placeholder="/*" defaultValue="/*" />
                </Form.Field>
                <Form.Field>
                    <label>Select Actions</label>
                    <Form.Dropdown
                        placeholder="Choose Actions"
                        multiple
                        selection
                        options={actionOptions}
                        value={actionList}
                        onChange={this.handleActionChange.bind(this)}
                    />
                </Form.Field>
                <Form.Button
                    fluid
                    onClick={this.handlePolicyAdd.bind(this)}
                >
                    Add Policy
                </Form.Button>
            </Form>
        );

        const policyList = this.state.policyList.map(policy => {
            return (
                <List.Item>
                    <Label horizontal basic>
                        {policy.targetType.toUpperCase()}
                        <Label.Detail>
                            {policy.targetValue} - {policy.actionList.map(s => s.toUpperCase()).join(", ")}
                        </Label.Detail>
                        <Icon onClick={this.handlePolicyDelete.bind(this, policy)} name='delete' />
                    </Label>
                </List.Item>
            );
        });

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
                        <List bulleted selection>
                            {policyList}
                        </List>
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

export function renderIAMSelfServiceWizard() {
    $('#new_policy_wizard').css('display', '');
    ReactDOM.render(
        <SelfService />,
        document.getElementById("new_policy_wizard"),
    );
}

export default SelfService;
